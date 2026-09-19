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
            short_response = client.post("/api/v1/notes", files=files[:9])
            assert short_response.status_code == 400

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

            analyze_response = client.post(f"/api/v1/notes/{job_id}/analyze")
            assert analyze_response.status_code == 200, analyze_response.text
            extraction = analyze_response.json()
            assert extraction["pages"][0]["source_name"] == "001.jpg"
            assert extraction["pages"][0]["elements"]
            assert (job_dir / "extraction.json").exists()

            delete_response = client.delete(f"/api/v1/notes/{job_id}")
            assert delete_response.status_code == 204
            assert not job_dir.exists()


if __name__ == "__main__":
    demo()
    print("phase1 api selfcheck ok")
