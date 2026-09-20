import io
import re
from html import escape
from pathlib import Path
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.schemas.document import ReconstructedDocument
from app.utils.cleanup import job_temp_dir


def pdf_text(value: Optional[str]) -> str:
    return escape(value or "")


_FORMULA_SCRIPT = re.compile(r"([_^])(?:\{([^{}]+)\}|\(([^()]*)\)|([A-Za-z0-9]+))")
_FORMULA_FRACTION = re.compile(r"\\frac\s*\{([^{}]+)\}\s*\{([^{}]+)\}")


def pdf_formula_text(value: Optional[str]) -> str:
    """Convert common OCR formula notation into ReportLab paragraph markup."""
    text = value or ""
    while _FORMULA_FRACTION.search(text):
        text = _FORMULA_FRACTION.sub(r"(\1) ÷ (\2)", text)
    for source, symbol in {
        r"\sum": "∑",
        r"\times": "×",
        r"\cdot": "·",
        r"\div": "÷",
        r"\leq": "≤",
        r"\geq": "≥",
        r"\neq": "≠",
        r"\left": "",
        r"\right": "",
    }.items():
        text = text.replace(source, symbol)
    text = escape(text).replace(" * ", " × ").replace(" / ", " ÷ ")

    def script(match: re.Match[str]) -> str:
        tag = "sub" if match.group(1) == "_" else "super"
        content = match.group(2) or match.group(3) or match.group(4) or ""
        return f"<{tag}>{content}</{tag}>"

    return _FORMULA_SCRIPT.sub(script, text)


def pdf_table_data(data: dict) -> tuple[list[str], list[list[str]]]:
    headers = data.get("headers", [])
    rows = data.get("rows", [])
    if not isinstance(headers, list) or not isinstance(rows, list):
        return [], []
    clean_rows = [[str(cell) for cell in row] for row in rows if isinstance(row, list)]
    width = max([len(headers), *(len(row) for row in clean_rows)], default=0)
    if not width:
        return [], []
    clean_headers = [str(cell) for cell in headers[:width]] + [""] * (width - len(headers))
    return clean_headers, [row[:width] + [""] * (width - len(row)) for row in clean_rows]


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas to compute and print 'Page X of Y' on every page, with 0.5in margins."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_header_footer(num_pages)
            super().showPage()
        super().save()

    def draw_header_footer(self, total_pages: int):
        self.saveState()
        self.setFont("Times-Roman", 9)
        self.setFillColor(colors.HexColor("#554F46"))

        # Margin is 0.5in = 36pt
        margin = 36
        page_width = letter[0]

        # Running Header on EVERY page
        doc_title = getattr(self, "doc_title", "MyNotes Lecture Document")
        self.drawString(margin, 762, str(doc_title)[:80])
        self.setStrokeColor(colors.HexColor("#D8CFC1"))
        self.setLineWidth(0.5)
        self.line(margin, 755, page_width - margin, 755)

        # Footer on all pages
        page_text = f"Page {self._pageNumber} of {total_pages}"
        self.drawRightString(page_width - margin, 22, page_text)
        self.drawString(margin, 22, "MyNotes Document Reconstruction")
        self.line(margin, 32, page_width - margin, 32)

        self.restoreState()


def render_pdf(reconstructed: ReconstructedDocument, style: str = "notebook") -> tuple[bytes, int]:
    buffer = io.BytesIO()

    # Notebook vs Clean color scheme
    is_notebook = style.lower() == "notebook"
    primary_color = colors.HexColor("#1A3A30") if is_notebook else colors.HexColor("#111827")
    accent_color = colors.HexColor("#4A3B2C") if is_notebook else colors.HexColor("#374151")
    border_color = colors.HexColor("#D5CAB6") if is_notebook else colors.HexColor("#E5E7EB")

    # Margin 0.5 in = 36 pt all around
    margin = 36
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=margin,
        rightMargin=margin,
        topMargin=margin + 16,
        bottomMargin=margin,
    )

    styles = getSampleStyleSheet()

    # Times New Roman font configuration with zero paragraph spacing
    styles.add(
        ParagraphStyle(
            "DocMainTitle",
            parent=styles["Normal"],
            fontName="Times-Bold",
            fontSize=20,
            leading=23,
            textColor=primary_color,
            spaceBefore=0,
            spaceAfter=6,
        )
    )

    styles.add(
        ParagraphStyle(
            "DocSectionTitle",
            parent=styles["Normal"],
            fontName="Times-Bold",
            fontSize=15,
            leading=18,
            textColor=primary_color,
            spaceBefore=8,
            spaceAfter=2,
            keepWithNext=True,
        )
    )

    styles.add(
        ParagraphStyle(
            "DocSubtitle",
            parent=styles["Normal"],
            fontName="Times-Bold",
            fontSize=12.5,
            leading=15.5,
            textColor=accent_color,
            spaceBefore=4,
            spaceAfter=2,
            keepWithNext=True,
        )
    )

    styles.add(
        ParagraphStyle(
            "DocBody",
            parent=styles["Normal"],
            fontName="Times-Roman",
            fontSize=11.5,
            leading=14.5,
            textColor=colors.HexColor("#24211D"),
            spaceBefore=0,
            spaceAfter=0,
        )
    )

    # Level 1 Bullet
    styles.add(
        ParagraphStyle(
            "DocBullet",
            parent=styles["Normal"],
            fontName="Times-Roman",
            fontSize=11.5,
            leading=14.5,
            textColor=colors.HexColor("#24211D"),
            leftIndent=16,
            firstLineIndent=-10,
            spaceBefore=0,
            spaceAfter=2,
        )
    )

    # Level 2 Sub-bullet (Indented further under parent point)
    styles.add(
        ParagraphStyle(
            "DocSubBullet",
            parent=styles["Normal"],
            fontName="Times-Roman",
            fontSize=11,
            leading=14,
            textColor=colors.HexColor("#332E27"),
            leftIndent=34,
            firstLineIndent=-10,
            spaceBefore=0,
            spaceAfter=2,
        )
    )

    # Numbered list item
    styles.add(
        ParagraphStyle(
            "DocNumbered",
            parent=styles["Normal"],
            fontName="Times-Roman",
            fontSize=11.5,
            leading=14.5,
            textColor=colors.HexColor("#24211D"),
            leftIndent=22,
            firstLineIndent=-14,
            spaceBefore=0,
            spaceAfter=2,
        )
    )

    styles.add(
        ParagraphStyle(
            "DocFormula",
            parent=styles["Normal"],
            fontName="Times-Italic",
            fontSize=12,
            leading=15,
            textColor=colors.HexColor("#1A3A30"),
            alignment=1,  # Centered
            spaceBefore=3,
            spaceAfter=3,
        )
    )

    styles.add(
        ParagraphStyle(
            "DocCaption",
            parent=styles["Normal"],
            fontName="Times-Italic",
            fontSize=10,
            leading=12,
            textColor=colors.HexColor("#5F5548"),
            alignment=1,
            spaceBefore=2,
            spaceAfter=4,
        )
    )

    story = []

    # Overall Document Main Title
    story.append(Paragraph(pdf_text(reconstructed.title), styles["DocMainTitle"]))
    story.append(
        HRFlowable(
            width="100%",
            thickness=1.5,
            color=primary_color,
            spaceBefore=1,
            spaceAfter=8,
        )
    )

    for section_idx, section in enumerate(reconstructed.sections):
        # Always render Section Title prominently on every section/title change
        if section.main_title:
            story.append(Paragraph(pdf_text(section.main_title), styles["DocSectionTitle"]))
            story.append(
                HRFlowable(
                    width="100%",
                    thickness=0.75,
                    color=border_color,
                    spaceBefore=1,
                    spaceAfter=4,
                )
            )

        numbered_counter = 1

        for elem in section.elements:
            elem_type = elem.type

            if elem_type in ["subtitle", "subtopic"]:
                numbered_counter = 1
                if elem.text:
                    story.append(Paragraph(pdf_text(elem.text), styles["DocSubtitle"]))

                # Render nested children
                for child in elem.children:
                    if child.type == "sub_bullet":
                        story.append(Paragraph(f"– &nbsp; {pdf_text(child.text)}", styles["DocSubBullet"]))
                    elif child.type == "numbered":
                        num = child.data.get("num", 1)
                        story.append(Paragraph(f"{num}. &nbsp; {pdf_text(child.text)}", styles["DocNumbered"]))
                    else:
                        story.append(Paragraph(f"• &nbsp; {pdf_text(child.text)}", styles["DocBullet"]))

            elif elem_type == "bullet":
                numbered_counter = 1
                if elem.text:
                    story.append(Paragraph(f"• &nbsp; {pdf_text(elem.text)}", styles["DocBullet"]))

            elif elem_type == "sub_bullet":
                numbered_counter = 1
                if elem.text:
                    # En-dash with deeper indentation
                    story.append(Paragraph(f"– &nbsp; {pdf_text(elem.text)}", styles["DocSubBullet"]))

            elif elem_type == "numbered":
                num = elem.data.get("num")
                if num is not None:
                    num_str = f"{num}."
                    numbered_counter = num + 1
                else:
                    num_str = f"{numbered_counter}."
                    numbered_counter += 1

                if elem.text:
                    story.append(Paragraph(f"{num_str} &nbsp; {pdf_text(elem.text)}", styles["DocNumbered"]))

            elif elem_type == "table":
                numbered_counter = 1
                headers, rows = pdf_table_data(elem.data)
                if rows:
                    if elem.text:
                        story.append(Paragraph(pdf_text(elem.text), styles["DocSubtitle"]))
                    has_headers = any(headers)
                    table_rows = ([headers] if has_headers else []) + rows
                    cell_rows = [
                        [Paragraph(pdf_text(cell), styles["DocBody"]) for cell in row]
                        for row in table_rows
                    ]
                    content_width = letter[0] - 2 * margin
                    table = Table(
                        cell_rows,
                        colWidths=[content_width / len(table_rows[0])] * len(table_rows[0]),
                        repeatRows=1 if has_headers else 0,
                    )
                    table_style = [
                        ("GRID", (0, 0), (-1, -1), 0.5, border_color),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 5),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ]
                    if has_headers:
                        table_style.extend([
                            ("BACKGROUND", (0, 0), (-1, 0), primary_color),
                            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ])
                    table.setStyle(TableStyle(table_style))
                    story.append(table)

            elif elem_type == "formula":
                numbered_counter = 1
                if elem.text:
                    formula_p = Paragraph(pdf_formula_text(elem.text), styles["DocFormula"])
                    table = Table(
                        [[formula_p]],
                        colWidths=[letter[0] - 2 * margin],
                    )
                    table.setStyle(
                        TableStyle(
                            [
                                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F4EEE4")),
                                ("BOX", (0, 0), (-1, -1), 0.5, border_color),
                                ("TOPPADDING", (0, 0), (-1, -1), 4),
                                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                            ]
                        )
                    )
                    story.append(table)

            elif elem_type == "caption":
                numbered_counter = 1
                if elem.text:
                    story.append(Paragraph(pdf_text(elem.text), styles["DocCaption"]))

            else:
                numbered_counter = 1
                if elem.text:
                    story.append(Paragraph(pdf_text(elem.text), styles["DocBody"]))

        story.append(Spacer(1, 4))

    canvas_maker = NumberedCanvas
    canvas_maker.doc_title = reconstructed.title

    doc.build(story, canvasmaker=canvas_maker)

    pdf_bytes = buffer.getvalue()

    page_count = max(1, pdf_bytes.count(b"/Type /Page\n") + pdf_bytes.count(b"/Type/Page\n") + pdf_bytes.count(b"/Type /Page\r"))
    if page_count == 0:
        page_count = 1

    return pdf_bytes, page_count
