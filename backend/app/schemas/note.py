from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.schemas.document import ReconstructedDocument


class NoteJobResponse(BaseModel):
    job_id: str
    status: str
    title: str
    image_count: int


class NoteStatusResponse(NoteJobResponse):
    progress: int
    created_at: datetime
    page_count: Optional[int] = None
    style: Optional[str] = None
    pdf_storage_key: Optional[str] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class NoteListItemResponse(BaseModel):
    job_id: str
    title: str
    status: str
    image_count: int
    page_count: Optional[int] = None
    style: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


class ReconstructionResponse(BaseModel):
    job_id: str
    status: str
    title: str
    page_count: int
    pdf_url: str
    download_url: str
    docx_download_url: str
    document: ReconstructedDocument
