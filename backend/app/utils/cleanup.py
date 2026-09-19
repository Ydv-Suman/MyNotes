import shutil
from datetime import datetime, timedelta
from pathlib import Path

from app.config import settings


def job_temp_dir(job_id: str) -> Path:
    return settings.temp_jobs_dir / job_id


def delete_temporary_job_files(job_id: str) -> None:
    shutil.rmtree(job_temp_dir(job_id), ignore_errors=True)


def cleanup_abandoned_jobs(max_age_hours: int = 24) -> int:
    root = settings.temp_jobs_dir
    if not root.exists():
        return 0

    cutoff = datetime.now().timestamp() - timedelta(hours=max_age_hours).total_seconds()
    removed = 0
    for path in root.iterdir():
        if path.is_dir() and path.stat().st_mtime < cutoff:
            shutil.rmtree(path, ignore_errors=True)
            removed += 1
    return removed

