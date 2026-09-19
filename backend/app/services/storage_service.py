from pathlib import Path

from app.config import settings


def ensure_storage_dir() -> Path:
    target = settings.permanent_pdfs_dir
    target.mkdir(parents=True, exist_ok=True)
    return target


def get_pdf_path(job_id: str) -> Path:
    return ensure_storage_dir() / f"{job_id}.pdf"


def save_pdf(job_id: str, pdf_bytes: bytes) -> Path:
    destination = get_pdf_path(job_id)
    destination.write_bytes(pdf_bytes)
    return destination


def pdf_exists(job_id: str) -> bool:
    return get_pdf_path(job_id).is_file()


def delete_pdf(job_id: str) -> bool:
    path = get_pdf_path(job_id)
    if path.is_file():
        path.unlink()
        return True
    return False
