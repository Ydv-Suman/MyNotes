from datetime import datetime
import logging
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.note import Note, NoteStatus
from app.schemas.document import ExtractionResult
from app.schemas.note import (
    NoteJobResponse,
    NoteListItemResponse,
    NoteStatusResponse,
    ReconstructionResponse,
)
from app.services.image_service import save_ordered_uploads, validate_uploads
from app.services.pdf_service import render_pdf
from app.services.reconstruction_service import reconstruct_document
from app.services.storage_service import delete_pdf, get_pdf_path, pdf_exists, save_pdf
from app.services.vision_service import extract_job_images, extraction_path
from app.utils.cleanup import delete_temporary_job_files
from app.utils.filename import sanitize_title

router = APIRouter(prefix="/api/v1/notes", tags=["notes"])
logger = logging.getLogger(__name__)
ALLOWED_STYLES = {"notebook", "clean"}


def progress_for(status_value: str) -> int:
    return {
        NoteStatus.CREATED.value: 5,
        NoteStatus.UPLOADING.value: 20,
        NoteStatus.UPLOADED.value: 35,
        NoteStatus.PREPROCESSING.value: 45,
        NoteStatus.ANALYZING.value: 60,
        NoteStatus.RECONSTRUCTING.value: 75,
        NoteStatus.RENDERING.value: 85,
        NoteStatus.GENERATING_PDF.value: 95,
        NoteStatus.COMPLETED.value: 100,
        NoteStatus.FAILED.value: 100,
        NoteStatus.CLEANED.value: 100,
    }.get(status_value, 0)


@router.get("", response_model=list[NoteListItemResponse])
def list_note_jobs(db: Session = Depends(get_db)) -> list[NoteListItemResponse]:
    notes = db.query(Note).order_by(desc(Note.created_at)).limit(50).all()
    return [
        NoteListItemResponse(
            job_id=note.id,
            title=note.title,
            status=note.status,
            image_count=note.image_count,
            page_count=note.page_count,
            style=note.style,
            created_at=note.created_at,
            completed_at=note.completed_at,
        )
        for note in notes
    ]


@router.post("", response_model=NoteJobResponse, status_code=status.HTTP_201_CREATED)
def create_note_job(
    files: list[UploadFile] = File(...),
    style: str = Form("notebook"),
    db: Session = Depends(get_db),
) -> NoteJobResponse:
    if style not in ALLOWED_STYLES:
        raise HTTPException(status_code=400, detail="Unsupported PDF style.")
    try:
        validate_uploads(files)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    note = Note(
        title=sanitize_title(files[0].filename.rsplit(".", 1)[0] if files[0].filename else "Untitled Notes"),
        status=NoteStatus.CREATED.value,
        image_count=len(files),
        style=style,
    )
    db.add(note)
    db.commit()
    db.refresh(note)

    try:
        note.status = NoteStatus.UPLOADING.value
        db.commit()
        save_ordered_uploads(note.id, files)
        note.status = NoteStatus.UPLOADED.value
        db.commit()
    except ValueError as exc:
        delete_temporary_job_files(note.id)
        note.status = NoteStatus.FAILED.value
        note.error_message = str(exc)
        db.commit()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        delete_temporary_job_files(note.id)
        note.status = NoteStatus.FAILED.value
        note.error_message = "Upload failed."
        db.commit()
        logger.exception("Upload failed for job %s", note.id)
        raise HTTPException(status_code=500, detail="Upload failed.") from exc

    return NoteJobResponse(
        job_id=note.id,
        status=note.status,
        title=note.title,
        image_count=note.image_count,
    )


@router.get("/{job_id}", response_model=NoteStatusResponse)
def get_note_job(job_id: str, db: Session = Depends(get_db)) -> NoteStatusResponse:
    note = db.get(Note, job_id)
    if note is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return NoteStatusResponse(
        job_id=note.id,
        status=note.status,
        title=note.title,
        image_count=note.image_count,
        progress=progress_for(note.status),
        created_at=note.created_at,
        page_count=note.page_count,
        style=note.style,
        pdf_storage_key=note.pdf_storage_key,
        completed_at=note.completed_at,
        error_message=note.error_message,
    )


@router.post("/{job_id}/analyze", response_model=ExtractionResult)
def analyze_note_job(job_id: str, db: Session = Depends(get_db)) -> ExtractionResult:
    note = db.get(Note, job_id)
    if note is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    if note.status == NoteStatus.FAILED.value:
        raise HTTPException(status_code=409, detail="Failed jobs cannot be analyzed.")

    try:
        note.status = NoteStatus.ANALYZING.value
        db.commit()
        result = extract_job_images(note.id)
        note.status = NoteStatus.RECONSTRUCTING.value
        db.commit()
        return result
    except Exception as exc:
        note.status = NoteStatus.FAILED.value
        note.error_message = "Image analysis failed."
        db.commit()
        logger.exception("Image analysis failed for job %s", note.id)
        raise HTTPException(status_code=500, detail="Image analysis failed.") from exc


@router.post("/{job_id}/reconstruct", response_model=ReconstructionResponse)
def reconstruct_and_render_job(job_id: str, db: Session = Depends(get_db)) -> ReconstructionResponse:
    note = db.get(Note, job_id)
    if note is None:
        raise HTTPException(status_code=404, detail="Job not found.")

    # Load extraction result
    ext_file = extraction_path(job_id)
    if not ext_file.is_file():
        raise HTTPException(status_code=400, detail="Run analysis before document reconstruction.")

    extraction = ExtractionResult.model_validate_json(ext_file.read_text(encoding="utf-8"))

    try:
        note.status = NoteStatus.RECONSTRUCTING.value
        db.commit()

        # Step 1: Hierarchical Document Reconstruction
        reconstructed = reconstruct_document(job_id, extraction, fallback_title=note.title)
        if reconstructed.title and reconstructed.title.lower() != "untitled notes":
            note.title = sanitize_title(reconstructed.title)

        # Step 2: Deterministic PDF Rendering
        note.status = NoteStatus.RENDERING.value
        db.commit()

        pdf_bytes, page_count = render_pdf(reconstructed, style=note.style or "notebook")

        # Step 3: Permanent PDF Storage
        note.status = NoteStatus.GENERATING_PDF.value
        db.commit()

        pdf_dest = save_pdf(job_id, pdf_bytes)

        # Step 4: Finalize note job in DB
        note.pdf_storage_key = str(pdf_dest)
        note.page_count = page_count
        note.completed_at = datetime.utcnow()
        note.status = NoteStatus.COMPLETED.value
        db.commit()

        # Requirement 53: Delete temporary source images after processing
        delete_temporary_job_files(job_id)

        return ReconstructionResponse(
            job_id=note.id,
            status=note.status,
            title=note.title,
            page_count=note.page_count or page_count,
            pdf_url=f"/api/v1/notes/{job_id}/pdf",
            download_url=f"/api/v1/notes/{job_id}/download",
            document=reconstructed,
        )
    except Exception as exc:
        note.status = NoteStatus.FAILED.value
        note.error_message = "PDF reconstruction failed."
        db.commit()
        logger.exception("PDF reconstruction failed for job %s", note.id)
        raise HTTPException(status_code=500, detail="PDF reconstruction failed.") from exc


@router.get("/{job_id}/pdf")
def view_note_pdf(job_id: str, db: Session = Depends(get_db)):
    note = db.get(Note, job_id)
    if note is None:
        raise HTTPException(status_code=404, detail="Job not found.")

    pdf_file = get_pdf_path(job_id)
    if not pdf_file.is_file():
        raise HTTPException(status_code=404, detail="Generated PDF not found.")

    return Response(
        content=pdf_file.read_bytes(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{quote(note.title)}.pdf"'},
    )


@router.get("/{job_id}/download")
def download_note_pdf(job_id: str, db: Session = Depends(get_db)):
    note = db.get(Note, job_id)
    if note is None:
        raise HTTPException(status_code=404, detail="Job not found.")

    pdf_file = get_pdf_path(job_id)
    if not pdf_file.is_file():
        raise HTTPException(status_code=404, detail="Generated PDF not found.")

    return Response(
        content=pdf_file.read_bytes(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{quote(note.title)}.pdf"'},
    )


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note_job(job_id: str, db: Session = Depends(get_db)) -> None:
    note = db.get(Note, job_id)
    if note is None:
        raise HTTPException(status_code=404, detail="Job not found.")

    delete_temporary_job_files(note.id)
    delete_pdf(note.id)
    db.delete(note)
    db.commit()
