import os
import sys
from types import ModuleType
from pathlib import Path
from tempfile import TemporaryDirectory


def demo() -> None:
    with TemporaryDirectory() as tmp:
        os.environ["DATABASE_URL"] = f"sqlite:///{Path(tmp) / 'test.db'}"

        pdf_service = ModuleType("app.services.pdf_service")
        pdf_service.render_pdf = None
        sys.modules[pdf_service.__name__] = pdf_service
        vision_service = ModuleType("app.services.vision_service")
        vision_service.extract_job_images = None
        vision_service.extraction_path = None
        sys.modules[vision_service.__name__] = vision_service
        multipart = ModuleType("multipart")
        multipart.__version__ = "0"
        multipart_parser = ModuleType("multipart.multipart")
        multipart_parser.parse_options_header = lambda value: value
        sys.modules["multipart"] = multipart
        sys.modules["multipart.multipart"] = multipart_parser
        sys.modules["python_multipart"] = multipart
        sys.modules["python_multipart.multipart"] = multipart_parser

        from app.api import notes
        from app.db import SessionLocal, init_db
        from app.models.note import Note, NoteStatus
        from app.schemas.document import ExtractionResult

        init_db()
        with SessionLocal() as db:
            note = Note(title="test", status=NoteStatus.UPLOADED.value, image_count=1)
            db.add(note)
            db.flush()
            job_id = note.id
            db.commit()

            def extract_without_open_transaction(requested_job_id: str) -> ExtractionResult:
                assert requested_job_id == job_id
                assert not db.in_transaction()
                return ExtractionResult(job_id=job_id, pages=[])

            notes.extract_job_images = extract_without_open_transaction
            notes.analyze_note_job(job_id, db)


if __name__ == "__main__":
    demo()
    print("db idle transaction selfcheck ok")
