Multimodal Handwritten Notes Generator

Final Project Specification

1. Project Overview

Build a web application that allows users to upload approximately 20–50 photos of handwritten or printed lecture/class notes and automatically convert them into a clean, structured PDF.

The system should understand the content of the images rather than simply performing OCR.

Core pipeline

User Photos
    ↓
Image Understanding
    ↓
Structured Document Reconstruction
    ↓
Visual / Diagram Reconstruction
    ↓
Deterministic PDF Rendering
    ↓
Permanent PDF Storage

The uploaded source photos are temporary processing inputs. They must not be stored permanently.

The generated PDF is stored permanently with an appropriate title.

2. Main Product Requirements

The application must:

Accept approximately 20–50 images per note-generation job.

Preserve the original order of uploaded pages.

Allow users to reorder images before processing.

Understand titles, subtitles, paragraphs, bullets, numbered lists, formulas, tables, diagrams, graphs, and images.

Preserve the hierarchy of the original notes.

Combine content that belongs to the same logical topic.

Preserve important subtopics instead of flattening everything into paragraphs.

Generate a clean PDF.

Give the generated PDF an appropriate title.

Permanently store the generated PDF.

Delete temporary source images after processing.

Provide progress information while processing.

Allow the user to preview/download the generated PDF.

Maintain a library of previously generated PDFs.

3. Important Document Structure Requirement

The system must not treat the input as a collection of independent images.

It must reconstruct the logical document.

For example:

Chapter 4

    Definition

        • Point 1
        • Point 2
        • Point 3

    Example

        Explanation of the example...

    Benefits

        • Benefit 1
        • Benefit 2

The following hierarchy must be preserved:

Main Title
    ↓
Subtitle / Subtopic
    ↓
Content
    ↓
Supporting Elements

Subtopics must remain separate.

The system must not convert:

Definition
Example
Benefits

into one large paragraph.

4. Repeated Titles Across Images

If multiple sequential images belong to the same main title, the system should recognize that they belong to one logical section.

Example:

Image 1:
Chapter 4
Definition
Point 1

Image 2:
Point 2
Point 3

Image 3:
Example
...

Image 4:
Important Formula
...

The final document should logically represent:

Chapter 4

Definition
    Point 1
    Point 2
    Point 3

Example
    ...

Important Formula
    ...

The title should not accidentally become a new section every time it appears in another image.

However, when a section continues onto another rendered PDF page, the main section title can be repeated at the top of the page when appropriate for readability.

5. Typography Requirements

All text must use Times New Roman.

Main Title

Font: Times New Roman
Size: 20 pt
Weight: Bold

Subtitle / Subtopic

Font: Times New Roman
Size: 16 pt
Weight: Bold

Regular Text

Font: Times New Roman
Size: 12 pt
Weight: Regular

Suggested additional formatting

Line spacing: approximately 1.15–1.3
Paragraph spacing: moderate
Bullet indentation: consistent
Section spacing: clear
Margins: notebook-friendly

The system should prioritize readability over trying to reproduce every pixel of the original photograph.

6. Handwritten Mode

The application should support a visual mode inspired by handwritten class notes.

However, because the required text font is Times New Roman, the handwritten appearance should primarily come from layout and visual treatment, not from replacing the font.

Possible visual elements:

Paper-like background

Light ruled lines

Underlines

Highlighting

Boxes around important concepts

Arrows

Small annotations

Controlled spacing variation

Handwritten-style diagram treatment

Notebook margins

Section separators

The actual text remains:

Times New Roman

If a true handwriting font is added later, it should be implemented as a separate style option.

7. Visual Content Requirements

The application must handle more than text.

Uploaded images may contain:

Semiconductor diagrams

Circuit diagrams

Flowcharts

Block diagrams

Graphs

Mathematical diagrams

Tables

Photographs

Technical drawings

Charts

Captions

Arrows and annotations

The system must identify these visual elements and preserve their relationship with nearby text.

8. Visual Classification

The AI reconstruction layer should classify content into categories such as:

text
formula
table
diagram
graph
photograph
image
caption
bullet
numbered_list
subtitle
main_title

Example:

{
  "type": "diagram",
  "image_id": "visual_7_1",
  "confidence": 0.94
}

9. Diagram Reconstruction

Simple diagrams can be reconstructed when the system has high confidence.

Examples:

Simple flowcharts

Basic circuit diagrams

Block diagrams

Simple graphs

Basic semiconductor structures

Concept diagrams

SVG should be used as an intermediate representation where appropriate.

Example:

Original Image
      ↓
Vision Model
      ↓
Diagram Structure
      ↓
SVG
      ↓
Handwritten-style transformation
      ↓
PDF

SVG is useful because it:

Preserves resolution.

Scales cleanly.

Allows controlled visual modifications.

Can be embedded into PDFs.

Makes simple diagrams deterministic.

10. Technical Accuracy Rule

The system must not automatically redraw complex technical diagrams just because the AI believes it can.

For technically sensitive diagrams such as:

Detailed semiconductor structures

Complicated circuits

Scientific diagrams

Engineering drawings

Complex graphs

the original cropped visual should be preserved when reconstruction confidence is low.

The priority is:

Technical Accuracy > Visual Style

If reconstruction could change the meaning of the original diagram, preserve the original image instead.

11. Photographs

Actual photographs should generally be:

Detected
    ↓
Cropped
    ↓
Placed in logical document position

They should not automatically be converted into artificial drawings.

The system may apply presentation styling such as:

Border

Caption

Notebook placement

Slight visual treatment

but the underlying photograph should remain accurate.

12. Caption Handling

Captions should remain associated with their visual element.

Example:

Figure 4.2 — PN Junction

[Diagram]

Explanation...

The system should avoid moving a caption far away from the diagram it describes.

13. Intermediate Document Model

The application should use an intermediate structured representation.

Recommended structure:

Document
 ├── Section
 │    ├── main_title
 │    └── Element
 │         ├── subtitle
 │         ├── paragraph
 │         ├── bullet
 │         ├── numbered
 │         ├── formula
 │         ├── image
 │         ├── diagram
 │         ├── graph
 │         ├── table
 │         └── caption

Example:

{
  "sections": [
    {
      "main_title": "Chapter 4",
      "elements": [
        {
          "type": "subtitle",
          "text": "Definition",
          "children": [
            {
              "type": "bullet",
              "text": "Point one"
            },
            {
              "type": "bullet",
              "text": "Point two"
            }
          ]
        }
      ]
    }
  ]
}

This intermediate representation is critical because the PDF renderer should not have to understand raw AI output.

14. Recommended Architecture

                    ┌─────────────────────┐
                    │       React         │
                    │    TypeScript UI    │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │       FastAPI       │
                    │       Backend       │
                    └──────────┬──────────┘
                               │
                 ┌─────────────┼─────────────┐
                 │             │             │
                 ▼             ▼             ▼
          PostgreSQL         Redis       Temporary Storage
          Metadata           Queue        Source Images
                 │             │
                 │             ▼
                 │       Python Worker
                 │             │
                 │             ▼
                 │      Image Processing
                 │             │
                 │             ▼
                 │       Vision AI
                 │             │
                 │             ▼
                 │    Structured JSON
                 │             │
                 │             ▼
                 │   Reconstruction Engine
                 │             │
                 │      ┌──────┼──────┐
                 │      ▼      ▼      ▼
                 │    Text   Formula Visual
                 │             │
                 │             ▼
                 │        PDF Renderer
                 │             │
                 │             ▼
                 └──── Permanent PDF Storage
                               │
                               ▼
                         React Download

15. FastAPI Backend Structure

Recommended backend structure:

backend/
  app/
    main.py

    api/
      notes.py
      downloads.py

    models/
      note.py

    schemas/
      note.py
      document.py

    services/
      image_service.py
      vision_service.py
      reconstruction_service.py
      pdf_service.py
      visual_service.py
      storage_service.py

    workers/
      note_worker.py

    utils/
      cleanup.py
      filename.py

    config.py

  fonts/
  tests/
  requirements.txt
  Dockerfile

16. API Endpoints

Create Note Job

POST /api/v1/notes

Uploads 20–50 images and creates a processing job.

The request should return quickly with a job ID.

Example:

{
  "job_id": "8d6c1d1e-...",
  "status": "CREATED"
}

Do not keep the HTTP request open while processing 50 images.

Get Job Status

GET /api/v1/notes/{job_id}

Example:

{
  "job_id": "8d6c1d1e-...",
  "status": "ANALYZING",
  "progress": 62,
  "title": "Chapter 4 Semiconductor Devices"
}

Download PDF

GET /api/v1/notes/{job_id}/download

The endpoint should return or securely stream the permanently stored PDF.

Delete Note

DELETE /api/v1/notes/{job_id}

Optional endpoint for deleting the user's stored PDF and metadata.

17. Database

PostgreSQL should store metadata, not source image blobs.

Recommended table:

CREATE TABLE notes (
    id UUID PRIMARY KEY,
    user_id UUID,
    title VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL,
    image_count INTEGER NOT NULL,
    page_count INTEGER,
    style VARCHAR(50),
    pdf_storage_key TEXT,
    created_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    error_message TEXT
);

The database should contain:

PDF metadata
Job status
User ownership
Title
Page count
Processing timestamps
Storage key
Errors

It should NOT contain:

Source image blobs
Raw uploaded photos
Large AI image payloads

18. Job Status Machine

Recommended states:

CREATED
   ↓
UPLOADING
   ↓
UPLOADED
   ↓
PREPROCESSING
   ↓
ANALYZING
   ↓
RECONSTRUCTING
   ↓
RENDERING
   ↓
GENERATING_PDF
   ↓
COMPLETED

Any processing state can transition to:

FAILED

Abandoned temporary jobs can transition to:

CLEANED

The job must only become:

COMPLETED

after the permanent PDF has successfully been stored.

19. Temporary Image Storage

During processing:

/tmp/note-jobs/{job_id}/
    001.jpg
    002.jpg
    003.jpg
    ...
    050.jpg

These files are temporary.

They must be deleted after processing.

Cleanup must happen on:

Successful processing

Failed processing

User cancellation

Worker errors

Server recovery

Abandoned jobs

A scheduled cleanup process is required because a server crash may occur before the normal cleanup code executes.

20. Permanent PDF Storage

Example:

notes/
  2026/
    09/
      {job_id}/
        chapter-4-semiconductor-devices.pdf

Only the generated PDF should remain permanently.

The title should be sanitized before becoming a filename.

21. Privacy Architecture

The system should enforce the following rule:

Source Images
     ↓
Temporary Processing
     ↓
PDF Generated
     ↓
Source Images Deleted
     ↓
PDF Stored Permanently

Never:

Source Images → Permanent Database

Never:

Source Images → Permanent Object Storage

Never:

Source Images → User Library

The user should only see the generated PDF in their permanent library.

22. Important Third-Party AI Privacy Consideration

Even if the application deletes its own temporary image files, the images may still be sent to an external vision/AI provider.

Therefore, the project must separately evaluate:

Provider data retention

Provider training policies

Whether API inputs are stored

Enterprise/API privacy controls

Data processing agreements where applicable

Regional storage requirements

Deleting the local image does not automatically mean the image has been deleted everywhere.

23. Security Requirements

Implement:

Authentication

Authorization

Per-user PDF ownership

UUID identifiers

File MIME/type validation

Maximum file size

Maximum aggregate upload size

Filename sanitization

Private object storage

Signed/temporary download URLs

Rate limiting

Per-user concurrent job limits

Secure secrets management

Minimal logging of sensitive data

Do not log raw source images.

Do not expose internal storage paths.

24. Processing Pipeline

Recommended processing flow:

1. Receive images
       ↓
2. Validate files
       ↓
3. Store temporarily
       ↓
4. Normalize image resolution
       ↓
5. Preprocess images
       ↓
6. Send images to vision model
       ↓
7. Extract structured content
       ↓
8. Detect relationships across pages
       ↓
9. Merge repeated sections
       ↓
10. Identify visuals
       ↓
11. Reconstruct safe/simple visuals
       ↓
12. Preserve complex visuals
       ↓
13. Generate deterministic PDF
       ↓
14. Store PDF permanently
       ↓
15. Delete source images
       ↓
16. Mark job COMPLETED

25. Image Preprocessing

Phone photos can be extremely large.

Before sending them to the AI model:

Correct orientation

Resize oversized images

Normalize compression

Remove unnecessary metadata

Improve contrast where useful

Detect blank pages

Crop excessive borders where safe

Do not unnecessarily send a 20–50 MB original phone photo to the vision model.

26. AI Extraction

The AI layer should extract:

Main titles

Subtitles

Paragraphs

Bullets

Numbered lists

Formulas

Tables

Captions

Diagrams

Graphs

Images

Page relationships

The output should be structured JSON rather than free-form text.

Example:

{
  "page": 7,
  "elements": [
    {
      "type": "subtitle",
      "text": "PN Junction"
    },
    {
      "type": "paragraph",
      "text": "A PN junction is..."
    },
    {
      "type": "diagram",
      "image_id": "page7_visual1",
      "confidence": 0.96
    }
  ]
}

27. Cross-Page Reconstruction

The AI/reconstruction layer must understand that a sentence, bullet list, or topic can continue across multiple images.

Example:

Image 1:
Definition:
  • Point 1
  • Point 2

Image 2:
  • Point 3
  • Point 4

Final result:

Definition:

• Point 1
• Point 2
• Point 3
• Point 4

The system must avoid incorrectly creating:

Definition

Definition

Definition

for every page.

28. Formula Handling

Mathematical formulas should be detected separately from normal text.

Possible pipeline:

Image
 ↓
Formula Detection
 ↓
Math Representation
 ↓
Formula Renderer
 ↓
PDF

The formula representation may use:

LaTeX

MathML

SVG

Another deterministic mathematical renderer

The final PDF should preserve mathematical readability.

29. Table Handling

Tables should be reconstructed as structured tables whenever confidence is sufficient.

Example:

| Property | Value |
|----------|-------|
| Voltage  | 5V    |
| Current  | 2A    |

If the table is too visually complex to reconstruct accurately, preserve the original cropped table image.

Again:

Accuracy > Reconstruction

30. PDF Generation

The PDF renderer should be deterministic.

It should receive the structured document model and render:

Main Titles
Subtitles
Paragraphs
Bullets
Formulas
Tables
Images
Diagrams
Graphs
Captions

The PDF renderer should not make semantic decisions.

Semantic decisions belong to the reconstruction layer.

31. Recommended Rendering Separation

Use:

Vision AI
    ↓
Structured Document Model
    ↓
Validation
    ↓
PDF Renderer

Do NOT build:

Vision AI
    ↓
Direct PDF

Direct AI-to-PDF generation makes layout debugging, testing, and consistency much harder.

32. React Frontend

Recommended structure:

frontend/
  src/
    components/
      ImageUploader.tsx
      ImagePreview.tsx
      ProcessingProgress.tsx
      PdfResult.tsx
      PdfLibrary.tsx

    pages/
      Home.tsx
      NoteDetail.tsx

    services/
      api.ts

    types/
      note.ts

33. User Flow

1. Open application
        ↓
2. Select 20–50 images
        ↓
3. Preview thumbnails
        ↓
4. Reorder images
        ↓
5. Select output style
        ↓
6. Click "Generate Notes"
        ↓
7. Receive Job ID
        ↓
8. Show processing progress
        ↓
9. Show generated title
        ↓
10. Show PDF preview/result
        ↓
11. Download PDF
        ↓
12. PDF appears in library

The frontend should never be responsible for deciding whether source images are deleted.

That must be enforced by the backend.

34. Progress Tracking

The UI should display stages such as:

Uploading
████████████████░░░░ 80%

Analyzing notes
██████████░░░░░░░░░░ 50%

Reconstructing document
██████░░░░░░░░░░░░░░ 30%

Generating PDF
████████████░░░░░░░░ 60%

Completed
████████████████████ 100%

The backend should be the source of truth for status.

35. Storage Rule

The application has two fundamentally different storage categories.

Temporary

Original uploaded photos

Lifetime:

Only during processing

Permanent

Generated PDF

Lifetime:

Until user deletes it

This distinction should be enforced architecturally.

36. Performance Requirements

The application must support 20–50 images without keeping an HTTP connection open for the entire processing period.

Use:

Background workers

Redis or another queue

Async processing

Image normalization

AI concurrency limits

Retry handling

Job progress tracking

Temporary isolated directories

Do not introduce Kafka, Kubernetes, or microservices unless the scale actually requires them.

A modular FastAPI application with workers is sufficient for the first production version.

37. Retry Strategy

AI calls and external storage operations can fail.

Use:

Bounded retries
+
Exponential backoff
+
Maximum retry count

Do not retry indefinitely.

Example:

Attempt 1
   ↓
2 seconds
   ↓
Attempt 2
   ↓
5 seconds
   ↓
Attempt 3
   ↓
FAILED

38. Failure Handling

The system must handle:

Invalid image

Oversized upload

Unsupported format

Vision API timeout

Vision API failure

AI malformed JSON

AI low-confidence extraction

Worker crash

PDF generation failure

Object storage failure

Database failure

User cancellation

A failed job must not leave source images permanently behind.

39. Successful Job Invariant

A successfully completed job should satisfy:

temporary source-image directory == absent

AND

permanent PDF == exists

AND

database status == COMPLETED

AND

database contains no source-image blobs

This is an important production invariant.

40. Testing Strategy

Test with:

Basic

20 images

50 images

Single section

Multiple sections

Structure

Repeated title

New title

Multiple subtitles

Nested bullets

Numbered lists

Paragraph continuation across pages

Visuals

Semiconductor diagrams

Circuit diagrams

Flowcharts

Graphs

Tables

Photographs

Technical drawings

Difficult inputs

Poor lighting

Blurry image

Skewed image

Handwriting

Mixed handwriting and printed text

Unreadable text

Missing pages

Failure

AI timeout

AI invalid response

Worker crash

PDF storage failure

Database failure

Cleanup failure

Privacy

Verify that after a successful job:

Temporary source files = 0

After a failed job:

Temporary source files = 0

After an abandoned job:

Temporary source files = 0

41. Important Test Cases

The following cases should explicitly be included:

1. Same title across 5 consecutive pages

2. Same title with capitalization differences

3. Same topic continuing across pages

4. A subtitle appearing on one page and its bullets continuing on another

5. Formula followed by explanation

6. Diagram followed by caption

7. Diagram embedded between two paragraphs

8. Complex technical diagram that should NOT be reconstructed

9. Simple flowchart that CAN be reconstructed

10. Photograph embedded in lecture notes

11. Table spanning multiple images

12. Worker crashes after AI analysis

13. PDF storage succeeds but database update fails

14. Database update succeeds only after PDF storage

15. Temporary image cleanup after every outcome

42. Production Data Flow

                   USER
                    │
                    ▼
             React Frontend
                    │
                    ▼
               FastAPI API
                    │
             Create Job ID
                    │
        ┌───────────┴───────────┐
        ▼                       ▼
 PostgreSQL                 Temp Storage
 Metadata                   Source Images
        │                       │
        └───────────┬───────────┘
                    ▼
               Job Queue
                    │
                    ▼
              Python Worker
                    │
                    ▼
            Image Processing
                    │
                    ▼
               Vision AI
                    │
                    ▼
          Structured Document
                    │
          ┌─────────┴─────────┐
          ▼                   ▼
     Text/Formula        Visual Content
          │                   │
          └─────────┬─────────┘
                    ▼
             PDF Renderer
                    │
                    ▼
           Permanent PDF Store
                    │
                    ▼
             Delete Temp Images
                    │
                    ▼
            Mark Job COMPLETED
                    │
                    ▼
              React Library

43. Suggested Technology Stack

Frontend

React
TypeScript
Vite
Tailwind CSS

Backend

Python
FastAPI
Pydantic
SQLAlchemy

Database

PostgreSQL

Queue

Redis

Worker

Python Worker

AI

Vision-capable AI model

The exact provider can be selected based on:

Vision quality

Cost

API limits

Data retention

Latency

Structured-output support

PDF

Use a deterministic PDF generation library capable of:

Font embedding

Images

SVG

Tables

Mathematical content

Page breaks

Headers/footers

44. Project Development Roadmap

Phase 1 — Upload & Privacy Boundary

Build:

React image uploader

20–50 image validation

Image preview

Image reordering

FastAPI upload endpoint

Temporary storage

PostgreSQL job metadata

Cleanup mechanism

Goal:

Upload → Temporary Storage → Delete

Phase 2 — AI Extraction

Build:

Image preprocessing

Vision API integration

Structured JSON extraction

Title detection

Subtitle detection

Paragraph detection

Bullet detection

Formula detection

Table detection

Visual detection

Goal:

Images → Structured Document

Phase 3 — Reconstruction

Build:

Cross-page merging

Repeated-title handling

Subtitle preservation

Section hierarchy

Formula representation

Visual classification

Confidence scoring

Goal:

Raw AI Output → Clean Document Model

Phase 4 — PDF Engine

Build:

Times New Roman typography

Main title styling

Subtitle styling

Body styling

Page layout

Notebook visual style

Formula rendering

Table rendering

SVG rendering

Image placement

Captions

Page breaks

Repeated section headers

Goal:

Document Model → High-quality PDF

Phase 5 — Product UI

Build:

Processing page

Progress indicator

PDF result page

PDF preview

Download button

PDF library

Delete PDF

Note title

Goal:

Complete end-to-end user experience

Phase 6 — Production Hardening

Add:

Authentication

Authorization

Rate limiting

Upload limits

Job limits

Retry handling

Monitoring

Logging

Cleanup scheduler

Error recovery

Storage security

AI cost tracking

45. Monitoring

Track:

Jobs created
Jobs completed
Jobs failed
Average processing time
AI processing time
PDF generation time
Average image count
AI cost per job
Storage usage
Cleanup failures
Worker failures

Useful infrastructure:

FastAPI
    ↓
Spring-like application metrics / Prometheus-compatible metrics
    ↓
Grafana

For the Python application, Prometheus-compatible instrumentation can be used.

46. Logging

Useful logs:

job_id
user_id
status
processing stage
duration
retry count
error type

Avoid logging:

Raw image content
Sensitive note contents
Private PDF contents
Unnecessary AI payloads

47. Critical Design Principle

The most important architectural decision is:

DO NOT BUILD:

Image → OCR → PDF

Instead build:

Image
  ↓
Image Understanding
  ↓
Structured Document Reconstruction
  ↓
Visual Reconstruction
  ↓
Deterministic PDF Rendering

This allows the system to understand the document instead of simply extracting text.

48. Critical Production Risks

Risk 1 — OCR-only architecture

Problem:

OCR extracts text but loses hierarchy.

Result:

Title
Subtitle
Bullet
Example

may become one large block.

Solution:

Use structured semantic extraction.

Risk 2 — AI directly generates the PDF

Problem:

Layout becomes unpredictable.

Solution:

Use:

AI → JSON
JSON → deterministic renderer

Risk 3 — Storing uploaded images

Problem:

Creates unnecessary privacy and storage risk.

Solution:

Use temporary storage with automatic cleanup.

Risk 4 — Complex diagram hallucination

Problem:

AI may generate a visually plausible but technically incorrect diagram.

Solution:

Use confidence thresholds and preserve the original visual when necessary.

Risk 5 — Long HTTP requests

Problem:

50-image processing may take too long.

Solution:

Use:

Job ID
+
Background Worker
+
Progress Tracking

Risk 6 — Cleanup only in success path

Problem:

Server crashes can leave source images behind.

Solution:

Use both:

finally cleanup
+
periodic abandoned-job cleanup

Risk 7 — Third-party AI retention

Problem:

Deleting local images does not guarantee third-party deletion.

Solution:

Review the AI provider's API data-handling and retention policy.

49. MVP Scope

The first version should focus on:

Upload 20–50 images
        ↓
Analyze
        ↓
Preserve hierarchy
        ↓
Preserve subtopics
        ↓
Handle formulas
        ↓
Handle basic diagrams
        ↓
Generate Times New Roman PDF
        ↓
Delete source images
        ↓
Store PDF

Do not initially build:

Microservices

Kubernetes

Kafka

Complex collaborative editing

Real-time multi-user editing

Advanced handwriting generation

Automatic redrawing of every technical diagram

These can be added later if the product requires them.

50. Final Product Definition

The final application is a multimodal lecture-note reconstruction system.

Its job is not simply to convert photos into text.

It should understand:

What is the title?
What is the subtitle?
Which content belongs to which section?
Which bullets belong together?
Which formula belongs to which explanation?
Which diagram belongs to which paragraph?
Which image should be preserved?
Which visual can safely be reconstructed?
Where should each element appear in the final PDF?

The complete architecture is:

┌─────────────────────────────────────────────┐
│                  USER                       │
└──────────────────────┬──────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────┐
│            REACT / TYPESCRIPT               │
│                                             │
│ Upload • Preview • Reorder • Progress       │
└──────────────────────┬──────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────┐
│                  FASTAPI                    │
│                                             │
│ Authentication • Jobs • API • Metadata      │
└──────────────┬──────────────────────────────┘
               │
       ┌───────┴────────┐
       ▼                ▼
 PostgreSQL           Redis
 Metadata             Queue
                         │
                         ▼
                ┌─────────────────┐
                │ Python Worker   │
                └────────┬────────┘
                         │
                         ▼
                Image Preprocessing
                         │
                         ▼
                   Vision AI
                         │
                         ▼
              Structured JSON Model
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
       Text / Formula          Visual Engine
              │                     │
              └──────────┬──────────┘
                         ▼
                  PDF Renderer
                         │
                         ▼
                 Permanent PDF
                         │
                         ▼
                 Delete Images
                         │
                         ▼
                 COMPLETED JOB
                         │
                         ▼
                  User Library

Core Principle

Understand the notes first. Render the PDF second.

The generated PDF is the permanent product.

The uploaded photos are temporary processing inputs.
