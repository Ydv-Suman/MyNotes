from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

ElementType = Literal[
    "main_title",
    "subtitle",
    "paragraph",
    "bullet",
    "sub_bullet",
    "numbered",
    "formula",
    "table",
    "diagram",
    "graph",
    "photograph",
    "image",
    "caption",
]


class DocumentElement(BaseModel):
    type: ElementType
    text: Optional[str] = None
    image_id: Optional[str] = None
    confidence: Optional[float] = Field(default=None, ge=0, le=1)
    children: list["DocumentElement"] = Field(default_factory=list)
    data: dict[str, Any] = Field(default_factory=dict)


class PageExtraction(BaseModel):
    image_number: int
    source_name: str
    main_title: Optional[str] = None
    elements: list[DocumentElement] = Field(default_factory=list)


class ExtractionResult(BaseModel):
    job_id: str
    pages: list[PageExtraction]


class DocumentSection(BaseModel):
    main_title: str
    elements: list[DocumentElement] = Field(default_factory=list)


class ReconstructedDocument(BaseModel):
    job_id: str
    title: str
    sections: list[DocumentSection] = Field(default_factory=list)
    total_elements: int = 0
