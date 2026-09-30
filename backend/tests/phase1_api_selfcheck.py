import os
import io
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image


def demo() -> None:
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        os.environ["DATABASE_URL"] = f"sqlite:///{root / 'test.db'}"
        os.environ["TEMP_JOBS_DIR"] = str(root / "jobs")

        from fastapi.testclient import TestClient

        from app.main import app

        image = io.BytesIO()
        Image.new("RGB", (1, 1)).save(image, format="JPEG")
        files = [
            ("files", (f"page-{index:02d}.jpg", image.getvalue(), "image/jpeg"))
            for index in range(1, 11)
        ]

        with TestClient(app) as client:
            oversized_files = [
                ("files", (f"page-{index:03d}.jpg", image.getvalue(), "image/jpeg"))
                for index in range(101)
            ]
            oversized_response = client.post("/api/v1/notes", files=oversized_files)
            assert oversized_response.status_code == 400

            response = client.post("/api/v1/notes", files=files, data={"style": "notebook"})
            assert response.status_code == 201, response.text
            payload = response.json()
            assert payload["status"] == "UPLOADED"
            assert payload["image_count"] == 10

            job_id = payload["job_id"]
            job_dir = root / "jobs" / job_id
            assert [path.name for path in sorted(job_dir.iterdir())][:3] == [
                "001.jpg",
                "002.jpg",
                "003.jpg",
            ]

            status_response = client.get(f"/api/v1/notes/{job_id}")
            assert status_response.status_code == 200
            assert status_response.json()["progress"] == 35

            from app.db import SessionLocal
            from app.models.note import Note, NoteStatus

            with SessionLocal() as db:
                note = db.get(Note, job_id)
                note.status = NoteStatus.ANALYZING.value
                db.commit()

            delete_response = client.delete(f"/api/v1/notes/{job_id}")
            assert delete_response.status_code == 409
            assert job_dir.exists()

            with SessionLocal() as db:
                note = db.get(Note, job_id)
                note.status = NoteStatus.FAILED.value
                db.commit()

            delete_response = client.delete(f"/api/v1/notes/{job_id}")
            assert delete_response.status_code == 204
            assert not job_dir.exists()


if __name__ == "__main__":
    demo()
    print("phase1 api selfcheck ok")
