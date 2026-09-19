from dataclasses import dataclass
from os import environ
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")


def database_url() -> str:
    value = environ.get("DATABASE_URL", f"sqlite:///{BASE_DIR / 'dev.db'}")
    if value.startswith("postgres://"):
        return value.replace("postgres://", "postgresql+psycopg://", 1)
    if value.startswith("postgresql://"):
        return value.replace("postgresql://", "postgresql+psycopg://", 1)
    return value


@dataclass(frozen=True)
class Settings:
    database_url: str = database_url()
    temp_jobs_dir: Path = Path(environ.get("TEMP_JOBS_DIR", "/tmp/note-jobs"))
    storage_dir: Path = Path(environ.get("STORAGE_DIR", str(BASE_DIR / "storage")))
    permanent_pdfs_dir: Path = Path(environ.get("PERMANENT_PDFS_DIR", str(BASE_DIR / "storage" / "pdfs")))
    static_dir: Path = Path(environ.get("STATIC_DIR", str(BASE_DIR.parent / "frontend" / "dist")))
    max_images: int = int(environ.get("MAX_IMAGES_PER_JOB", "50"))
    min_images: int = int(environ.get("MIN_IMAGES_PER_JOB", "10"))
    max_file_bytes: int = int(environ.get("MAX_IMAGE_MB", "25")) * 1024 * 1024
    max_batch_bytes: int = int(environ.get("MAX_BATCH_MB", "500")) * 1024 * 1024
    vision_provider: str = environ.get("VISION_PROVIDER", "openai")
    openai_api_key: str = environ.get("OPENAI_API_KEY", "")


settings = Settings()
