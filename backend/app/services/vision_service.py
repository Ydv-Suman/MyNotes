import base64
from concurrent.futures import ThreadPoolExecutor
import json
import logging
from pathlib import Path
import re
import subprocess
import sys
from typing import Optional

from openai import OpenAI

from app.config import settings
from app.schemas.document import DocumentElement, ExtractionResult, PageExtraction
from app.utils.cleanup import job_temp_dir
from app.utils.files import ALLOWED_EXTENSIONS

logger = logging.getLogger("vision_service")

BIN_OCR = Path(__file__).resolve().parents[1] / "bin" / "ocr_helper"

FOOTER_METADATA = re.compile(
    r"^(?:instructor|professor|lecturer|teacher|presented by|prepared by|date|course|class|section|semester|term)\s*[:\-]",
    re.IGNORECASE,
)
FOOTER_DATE = re.compile(
    r"^(?:(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|"
    r"sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+\d{1,2}(?:st|nd|rd|th)?(?:,\s*\d{2,4})?"
    r"|\d{1,2}[/.\-]\d{1,2}[/.\-]\d{2,4})$",
    re.IGNORECASE,
)


def is_footer_metadata(text: str) -> bool:
    """Recognize administrative footer text without removing dates in note content."""
    normalized = " ".join(text.strip().split())
    return bool(FOOTER_METADATA.match(normalized) or FOOTER_DATE.match(normalized))


def remove_footer_metadata(lines: list[str]) -> list[str]:
    footer_start = max(1, len(lines) - 3)  # Never discard the page's title line.
    return [
        line for index, line in enumerate(lines)
        if index < footer_start or not is_footer_metadata(line)
    ]


def extraction_path(job_id: str) -> Path:
    return job_temp_dir(job_id) / "extraction.json"


def encode_image_base64(image_path: Path) -> str:
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def get_image_mime(image_path: Path) -> str:
    suffix = image_path.suffix.lower()
    if suffix in [".jpg", ".jpeg"]:
        return "image/jpeg"
    if suffix == ".png":
        return "image/png"
    if suffix == ".webp":
        return "image/webp"
    return "image/jpeg"


def extract_single_page_openai(client: OpenAI, image_path: Path, image_index: int) -> Optional[PageExtraction]:
    try:
        mime = get_image_mime(image_path)
        b64 = encode_image_base64(image_path)
        data_url = f"data:{mime};base64,{b64}"

        prompt = (
            "Transcribe the lecture slide/notes in this image into structured JSON.\n"
            "Identify the main slide title, level-1 bullet points, level-2 sub-bullets, and numbered items.\n"
            "Return JSON matching:\n"
            "{\n"
            '  "main_title": "Slide Title",\n'
            '  "elements": [\n'
            '    {"type": "bullet", "text": "Level-1 bullet text"},\n'
            '    {"type": "sub_bullet", "text": "Level-2 sub-bullet text"},\n'
            '    {"type": "numbered", "text": "Numbered item", "num": 1},\n'
            '    {"type": "subtitle", "text": "Subtopic heading if present"},\n'
            '    {"type": "paragraph", "text": "Body text"}\n'
            "  ]\n"
            "}\n"
            "Extract exact text and formulas. Do not return raw images or dummy descriptions.\n"
            "Ignore administrative metadata, especially near the bottom of the image: instructor/professor names, "
            "dates, course/class/section labels, semesters, terms, and similar slide footer text."
        )

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": data_url, "detail": "low"}},
                    ],
                }
            ],
            response_format={"type": "json_object"},
            max_tokens=1500,
            timeout=25.0,
        )

        raw_json = response.choices[0].message.content or "{}"
        parsed = json.loads(raw_json)

        elements: list[DocumentElement] = []
        for elem_data in parsed.get("elements", []):
            elem_type = elem_data.get("type", "paragraph")
            text = elem_data.get("text", "").strip()
            if not text:
                continue

            num = elem_data.get("num")
            elements.append(
                DocumentElement(
                    type=elem_type,
                    text=text,
                    confidence=0.95,
                    data={"num": num} if num is not None else {},
                )
            )

        title = parsed.get("main_title") or f"Page {image_index}"
        footer_start = max(0, len(elements) - 3)
        elements = [
            element for index, element in enumerate(elements)
            if index < footer_start or not is_footer_metadata(element.text or "")
        ]
        return PageExtraction(
            image_number=image_index,
            source_name=image_path.name,
            main_title=title,
            elements=elements,
        )
    except Exception as exc:
        logger.warning(f"OpenAI extraction failed for page {image_index} ({exc}), using local Apple Vision OCR.")
        return None


def extract_single_page_local_ocr(image_path: Path, image_index: int) -> PageExtraction:
    """Uses native Apple Vision OCR to extract text details with hierarchical bullets and sub-bullets."""
    raw_lines: list[dict] = []
    if sys.platform == "darwin" and BIN_OCR.is_file():
        try:
            res = subprocess.run(
                [str(BIN_OCR), str(image_path)],
                capture_output=True,
                text=True,
                timeout=20.0,
            )
            if res.returncode == 0 and res.stdout.strip():
                raw_lines = json.loads(res.stdout)
        except Exception as exc:
            logger.error(f"Local OCR failed on {image_path.name}: {exc}")
    else:
        try:
            res = subprocess.run(
                ["tesseract", str(image_path), "stdout"],
                capture_output=True,
                text=True,
                timeout=30.0,
            )
            if res.returncode == 0:
                raw_lines = [{"text": line} for line in res.stdout.splitlines()]
        except Exception as exc:
            logger.error(f"Tesseract OCR failed on {image_path.name}: {exc}")

    # Filter out empty lines and noise symbols
    clean_lines: list[str] = []
    for l in raw_lines:
        t = l.get("text", "").strip()
        if not t or t in ["→", ">", ">>", "...", "■", "▪", "•", "-", "*"]:
            continue
        clean_lines.append(t)

    clean_lines = remove_footer_metadata(clean_lines)

    if not clean_lines:
        return PageExtraction(
            image_number=image_index,
            source_name=image_path.name,
            main_title=f"Page {image_index}",
            elements=[],
        )

    # Step 1: Substring & fragment deduplication
    deduped_lines: list[str] = []
    for line in clean_lines:
        if deduped_lines:
            prev = deduped_lines[-1]
            if line.lower().startswith(prev.lower()) and len(line) > len(prev):
                deduped_lines[-1] = line
                continue
            if prev.lower().startswith(line.lower()):
                continue
            if prev.lower() == line.lower():
                continue
        deduped_lines.append(line)

    if not deduped_lines:
        return PageExtraction(
            image_number=image_index,
            source_name=image_path.name,
            main_title=f"Page {image_index}",
            elements=[],
        )

    # Step 2: The top line is the slide/page title
    page_title = deduped_lines[0].strip()
    content_lines = deduped_lines[1:]

    # Step 3: Parse elements with hierarchical level 1 bullets and level 2 sub-bullets
    elements: list[DocumentElement] = []

    for line in content_lines:
        # Level 1 major bullet: circle bullet glyphs
        b1_match = re.match(r"^([•\u2022\u2023\u25E6\u2043\u2219]|o\s+|E\s+)\s*(.*)", line)
        # Level 2 sub-bullet: dashes or sub-point indicators
        b2_match = re.match(r"^([–—\-\>])\s*(.*)", line)
        # Numbered item: 1., 2., etc.
        n_match = re.match(r"^(\d+)[\.\)]\s*(.*)", line)

        if b1_match:
            b_text = b1_match.group(2).strip() or line
            elements.append(DocumentElement(type="bullet", text=b_text))

        elif b2_match:
            sub_text = b2_match.group(2).strip() or line
            elements.append(DocumentElement(type="sub_bullet", text=sub_text))

        elif n_match:
            num = int(n_match.group(1))
            n_text = n_match.group(2).strip() or line
            elements.append(
                DocumentElement(
                    type="numbered",
                    text=n_text,
                    data={"num": num},
                )
            )

        elif line.endswith(":") or line.startswith(("Topic:", "Note:", "Theorem:", "Definition:")):
            elements.append(DocumentElement(type="subtitle", text=line.rstrip(":")))

        elif any(sym in line for sym in ["=", "≠", "≤", "≥", "∑", "∫", "√", "×", "÷"]) and len(line) < 50:
            elements.append(DocumentElement(type="formula", text=line))

        else:
            # Sentence continuation: merge with preceding bullet or sub-bullet
            if elements and elements[-1].type in ["bullet", "sub_bullet", "paragraph"]:
                prev_text = elements[-1].text or ""
                if not prev_text.endswith((".", "?", "!")) or line[0].islower():
                    elements[-1].text = f"{prev_text} {line}"
                    continue

            elements.append(DocumentElement(type="paragraph", text=line))

    return PageExtraction(
        image_number=image_index,
        source_name=image_path.name,
        main_title=page_title,
        elements=elements,
    )


def extract_job_images(job_id: str) -> ExtractionResult:
    images = sorted(
        path for path in job_temp_dir(job_id).iterdir() if path.suffix.lower() in ALLOWED_EXTENSIONS
    )
    if not images:
        raise ValueError("No temporary images found for this job.")

    client: Optional[OpenAI] = None
    if settings.openai_api_key and settings.openai_api_key.strip():
        try:
            client = OpenAI(api_key=settings.openai_api_key.strip())
        except Exception as exc:
            logger.warning(f"Could not initialize OpenAI client: {exc}")

    def process_page(item: tuple[int, Path]) -> PageExtraction:
        idx, img = item
        if client:
            extracted = extract_single_page_openai(client, img, idx)
            if extracted and extracted.elements:
                return extracted
        return extract_single_page_local_ocr(img, idx)

    with ThreadPoolExecutor(max_workers=6) as executor:
        pages = list(executor.map(process_page, enumerate(images, start=1)))

    if not any(page.elements for page in pages):
        raise RuntimeError("No note text could be extracted. Check image clarity or AI vision billing.")

    result = ExtractionResult(job_id=job_id, pages=pages)
    extraction_path(job_id).write_text(result.model_dump_json(indent=2), encoding="utf-8")
    return result
