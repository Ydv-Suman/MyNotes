import json
from pathlib import Path
from typing import Optional

from app.schemas.document import (
    DocumentElement,
    DocumentSection,
    ExtractionResult,
    ReconstructedDocument,
)
from app.utils.cleanup import job_temp_dir


def reconstruction_path(job_id: str) -> Path:
    return job_temp_dir(job_id) / "reconstructed.json"


def normalize_title(title: Optional[str]) -> str:
    if not title or not title.strip():
        return ""
    return " ".join(title.strip().split())


def reconstruct_document(job_id: str, extraction: ExtractionResult, fallback_title: str = "Class Notes") -> ReconstructedDocument:
    sections: list[DocumentSection] = []
    current_section: Optional[DocumentSection] = None
    seen_in_current_section: set[str] = set()
    total_elements = 0

    # Determine document title from earliest non-generic main_title or fallback
    doc_title = fallback_title
    for page in extraction.pages:
        norm = normalize_title(page.main_title)
        if norm and norm.lower() not in ["untitled notes", "untitled", ""]:
            doc_title = norm
            break

    for page in extraction.pages:
        page_title = normalize_title(page.main_title) or doc_title

        # Check if this page belongs to the current section or starts a new logical section
        if current_section is None or (page_title and page_title.lower() != current_section.main_title.lower()):
            current_section = DocumentSection(
                main_title=page_title,
                elements=[],
            )
            sections.append(current_section)
            seen_in_current_section = set()

        # Append page elements preserving subtopics, bullets, formulas, and visual diagrams
        for elem in page.elements:
            # Avoid repeating main_title as an element inside the section
            if elem.type == "main_title" and normalize_title(elem.text).lower() == current_section.main_title.lower():
                continue

            # Deduplicate items across repeated photos / build slides of the same topic
            norm_elem = f"{elem.type}:{' '.join((elem.text or '').lower().split())}"
            if elem.text and norm_elem in seen_in_current_section:
                continue
            if elem.text:
                seen_in_current_section.add(norm_elem)

            current_section.elements.append(elem)
            total_elements += 1
            if elem.children:
                total_elements += len(elem.children)

    # If no sections were created, generate a fallback section
    if not sections:
        sections = [
            DocumentSection(
                main_title=doc_title,
                elements=[DocumentElement(type="paragraph", text="No structured elements detected.")],
            )
        ]

    reconstructed = ReconstructedDocument(
        job_id=job_id,
        title=doc_title,
        sections=sections,
        total_elements=total_elements,
    )

    try:
        reconstruction_path(job_id).write_text(
            reconstructed.model_dump_json(indent=2), encoding="utf-8"
        )
    except Exception:
        pass

    return reconstructed
