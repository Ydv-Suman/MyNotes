import shutil
from pathlib import Path

from fastapi import UploadFile

from app.config import settings
from app.utils.cleanup import job_temp_dir
from app.utils.files import ordered_image_name, validate_image_batch, validate_image_content


def validate_uploads(files: list[UploadFile]) -> None:
    validate_image_batch(
        [file.filename or "" for file in files],
        [file.content_type for file in files],
        settings.min_images,
        settings.max_images,
    )


def save_ordered_uploads(job_id: str, files: list[UploadFile]) -> list[Path]:
    target = job_temp_dir(job_id)
    target.mkdir(parents=True, exist_ok=False)

    saved: list[Path] = []
    batch_bytes = 0
    for index, file in enumerate(files, start=1):
        destination = target / ordered_image_name(index, file.filename or "", file.content_type)
        written = 0
        with destination.open("wb") as output:
            while chunk := file.file.read(1024 * 1024):
                written += len(chunk)
                batch_bytes += len(chunk)
                if written > settings.max_file_bytes:
                    raise ValueError(f"{file.filename} exceeds the per-image size limit.")
                if batch_bytes > settings.max_batch_bytes:
                    raise ValueError("Upload exceeds the total batch size limit.")
                output.write(chunk)
        validate_image_content(destination)
        saved.append(destination)
    return saved
