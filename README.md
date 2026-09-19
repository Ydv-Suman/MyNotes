# MyNotes

MyNotes converts photos of handwritten or printed class notes into a clean, structured PDF. Upload existing images or capture pages directly from the browser camera, arrange them in order, and generate downloadable notes.

## Features

- Upload, paste, drag, or capture 10-50 note images
- Live camera preview with supported hardware zoom controls
- Reorder and remove pages before processing
- OpenAI vision extraction with Linux Tesseract OCR fallback
- Removes common slide footer metadata such as instructor names and dates
- Reconstructs titles, paragraphs, bullets, numbered lists, formulas, and captions
- Notebook and clean PDF color styles
- PDF preview, download, deletion, and notes library
- Persistent database metadata and generated PDF storage
- Separate production containers for the React frontend and FastAPI backend

## Architecture

```text
Browser
  |
  v
Nginx / React frontend :8080
  |
  | /api
  v
FastAPI backend :8000
  |-- OpenAI Vision
  |-- Tesseract fallback
  |-- PostgreSQL or SQLite
  `-- Persistent PDF storage
```

## Technology

- Frontend: React, TypeScript, Vite
- Backend: FastAPI, SQLAlchemy, ReportLab, Pillow
- AI/OCR: OpenAI vision and Tesseract
- Database: PostgreSQL in production or SQLite locally
- Deployment: Docker, Docker Compose, Nginx, AWS EC2/ECS compatible

## Project Structure

```text
MyNotes/
├── backend/
│   ├── app/
│   ├── tests/
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   ├── Dockerfile
│   └── nginx.conf.template
├── docker-compose/
│   ├── compose.yml
│   ├── .env.example
│   └── README.md
└── README.md
```

## Quick Start with Docker Compose

Requirements:

- Docker Desktop or Docker Engine
- Docker Compose plugin
- An OpenAI API key with available API credits

From the project root:

```bash
cp docker-compose/.env.example docker-compose/.env
```

Edit `docker-compose/.env` and set:

```dotenv
OPENAI_API_KEY=your-new-api-key
APP_PORT=8080
```

Build and start the application:

```bash
cd docker-compose
docker compose up -d --build
docker compose ps
```

Open [http://localhost:8080](http://localhost:8080).

Useful commands:

```bash
# Follow logs
docker compose logs -f

# Rebuild after source changes
docker compose up -d --build

# Restart only the backend after changing .env
docker compose up -d --force-recreate backend

# Stop containers while preserving data
docker compose down

# Stop containers and permanently delete local application data
docker compose down --volumes
```

The initial `pull access denied` warning for the local `mynotes-*` images is harmless when Compose subsequently builds them successfully.

## Local Development without Docker

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The backend loads `backend/.env`. Without `DATABASE_URL`, it uses `backend/dev.db`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173).

## Configuration

| Variable | Required | Default | Description |
|---|---:|---|---|
| `OPENAI_API_KEY` | Recommended | Empty | Enables AI vision extraction |
| `DATABASE_URL` | No | SQLite | SQLAlchemy database URL |
| `APP_PORT` | No | `8080` | Host port used by Docker Compose |
| `MIN_IMAGES_PER_JOB` | No | `10` | Minimum images in a job |
| `MAX_IMAGES_PER_JOB` | No | `50` | Maximum images in a job |
| `MAX_IMAGE_MB` | No | `25` | Per-image upload limit |
| `MAX_BATCH_MB` | No | `500` | Total upload limit |
| `PERMANENT_PDFS_DIR` | No | `/data/pdfs` in Docker | Generated PDF location |

Both `postgresql://` and `postgresql+psycopg://` database URLs are supported.

## OCR Behavior

OpenAI vision provides the best result for handwritten notes and complex lecture slides. If the API is unavailable or has no remaining credits, the Linux container falls back to Tesseract. Tesseract works best with clear printed text and may be less accurate with handwriting, formulas, diagrams, or low-resolution images.

The application does not generate placeholder `Content from ...` PDFs. If neither extraction method finds note text, the job fails instead of producing a misleading document.

## Tests

Run from the project root:

```bash
PYTHONPATH=backend backend/.venv/bin/python backend/tests/security_selfcheck.py
PYTHONPATH=backend backend/.venv/bin/python backend/tests/phase1_selfcheck.py
OPENAI_API_KEY= PYTHONPATH=backend backend/.venv/bin/python backend/tests/phase1_api_selfcheck.py
npm --prefix frontend run build
```

## Deploy on a Single AWS EC2 Instance

For personal use, one EC2 instance running Docker Compose is sufficient.

Recommended starting configuration:

- Ubuntu LTS
- `t3.medium` or larger
- At least 20 GB encrypted EBS storage
- Elastic IP or domain name
- Security group allowing SSH only from your IP
- HTTPS access to the frontend

Install Docker on the instance, clone this repository, create `docker-compose/.env`, and run:

```bash
cd MyNotes/docker-compose
docker compose up -d --build
docker compose ps
docker compose logs -f
```

Only the frontend should be publicly reachable. Do not expose backend port `8000` directly.

Browser camera APIs require HTTPS outside `localhost`. Put the EC2 application behind an AWS Application Load Balancer with an ACM certificate, or configure an HTTPS reverse proxy. Restrict inbound access to your IP if the application is only for personal use.

Docker Compose stores PDFs and its default SQLite database in the `mynotes-data` volume. This survives container recreation but not deletion of the EC2 instance and its EBS volume. Create EBS snapshots or use PostgreSQL plus EFS for stronger persistence.

## Deploy Images to Amazon ECR

Create separate ECR repositories for `mynotes-backend` and `mynotes-frontend`. On Apple Silicon, build AWS-compatible AMD64 images explicitly:

```bash
docker buildx build --platform linux/amd64 -t YOUR_ECR/mynotes-backend:v1 --push ./backend
docker buildx build --platform linux/amd64 -t YOUR_ECR/mynotes-frontend:v1 --push ./frontend
```

Use immutable version tags such as `v1`, `v2`, and `v3` rather than replacing `latest` in production.

## Security

- Never commit `.env` files or API keys.
- Store production secrets in AWS Secrets Manager or protected EC2 environment files.
- Rotate any key that has been displayed in logs, terminals, screenshots, or chat.
- Keep backend port `8000` private.
- Use HTTPS for camera access and uploaded note privacy.
- Uploaded files are size-limited and validated as real image data.
- Temporary source images are deleted after successful PDF generation.

## Current Scope

MyNotes is currently designed as a private, single-user application. It does not include account registration or multi-user authorization. Add authentication and per-user ownership checks before exposing it as a public service.
# MyNotes
