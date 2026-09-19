from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class NoteStatus(str, Enum):
    CREATED = "CREATED"
    UPLOADING = "UPLOADING"
    UPLOADED = "UPLOADED"
    PREPROCESSING = "PREPROCESSING"
    ANALYZING = "ANALYZING"
    RECONSTRUCTING = "RECONSTRUCTING"
    RENDERING = "RENDERING"
    GENERATING_PDF = "GENERATING_PDF"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CLEANED = "CLEANED"


class Note(Base):
    __tablename__ = "notes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default=NoteStatus.CREATED.value)
    image_count: Mapped[int] = mapped_column(Integer, nullable=False)
    page_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    style: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    pdf_storage_key: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
