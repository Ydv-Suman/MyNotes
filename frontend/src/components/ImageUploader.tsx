import {
  ChangeEvent,
  DragEvent,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState
} from "react";

import {
  analyzeNoteJob,
  createNoteJob,
  deleteNoteJob,
  fetchNotesLibrary,
  getDocxDownloadUrl,
  getPdfDownloadUrl,
  getPdfViewUrl,
  reconstructNoteJob
} from "../services/api";
import type {
  ExtractionResult,
  NoteJob,
  NoteListItem,
  ReconstructionResponse
} from "../types/note";

type PreviewImage = {
  id: string;
  file: File;
  url: string;
  sizeFormatted: string;
};

const MIN_IMAGES = 1;
const MAX_IMAGES = 100;

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function ImageUploader() {
  const [images, setImages] = useState<PreviewImage[]>([]);
  const [style, setStyle] = useState("notebook");
  const [job, setJob] = useState<NoteJob | null>(null);
  const [extraction, setExtraction] = useState<ExtractionResult | null>(null);
  const [reconstruction, setReconstruction] = useState<ReconstructionResponse | null>(null);

  const [currentStep, setCurrentStep] = useState<
    "idle" | "uploading" | "analyzing" | "reconstructing" | "completed"
  >("idle");
  const [error, setError] = useState("");
  const [isDragOver, setIsDragOver] = useState(false);
  const [draggedCardIndex, setDraggedCardIndex] = useState<number | null>(null);
  const [dragOverCardIndex, setDragOverCardIndex] = useState<number | null>(null);

  // Modals & Drawers
  const [previewModalImage, setPreviewModalImage] = useState<PreviewImage | null>(null);
  const [activePdfModalJobId, setActivePdfModalJobId] = useState<string | null>(null);
  const [isLibraryOpen, setIsLibraryOpen] = useState(false);
  const [libraryItems, setLibraryItems] = useState<NoteListItem[]>([]);
  const [isExpandedHierarchy, setIsExpandedHierarchy] = useState(false);
  const [isCameraOpen, setIsCameraOpen] = useState(false);
  const [activeView, setActiveView] = useState<"home" | "about">("home");
  const [cameraZoom, setCameraZoom] = useState<{ min: number; max: number; step: number; value: number } | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const cameraStreamRef = useRef<MediaStream | null>(null);
  const imagesRef = useRef<PreviewImage[]>([]);
  const dragCounter = useRef(0);

  imagesRef.current = images;

  const countStatus = useMemo(() => {
    if (images.length === 0) return "Add 1–100 note pages";
    if (images.length < MIN_IMAGES) return `${MIN_IMAGES - images.length} more needed (min ${MIN_IMAGES})`;
    if (images.length > MAX_IMAGES) return `${images.length - MAX_IMAGES} too many (max ${MAX_IMAGES})`;
    return "Ready to generate";
  }, [images.length]);

  const isValidCount = images.length >= MIN_IMAGES && images.length <= MAX_IMAGES;

  const progressPercentage = useMemo(() => {
    if (images.length === 0) return 0;
    return Math.min(100, Math.round((images.length / MIN_IMAGES) * 100));
  }, [images.length]);

  // Load Library notes
  const loadLibrary = useCallback(async () => {
    try {
      const items = await fetchNotesLibrary();
      setLibraryItems(items);
    } catch {
      // Non-blocking if library fails initially
    }
  }, []);

  useEffect(() => {
    loadLibrary();
  }, [loadLibrary]);

  // Append new files safely with preview URLs
  const handleIncomingFiles = useCallback((incoming: FileList | File[]) => {
    const rawFiles = Array.from(incoming);
    const validImageFiles = rawFiles.filter((file) => {
      const isImgType = file.type.startsWith("image/");
      const isImgExt = /\.(jpe?g|png|webp|heic|heif)$/i.test(file.name);
      return isImgType || isImgExt;
    });

    if (validImageFiles.length < rawFiles.length) {
      setError("Some unsupported files were skipped. Only JPG, PNG, WEBP, and HEIC are supported.");
    } else {
      setError("");
    }

    if (validImageFiles.length === 0) return;

    setJob(null);
    setExtraction(null);
    setReconstruction(null);
    setCurrentStep("idle");

    setImages((current) => {
      const newItems: PreviewImage[] = validImageFiles.map((file, index) => ({
        id: `${file.name}-${file.lastModified}-${index}-${globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random()}`}`,
        file,
        url: URL.createObjectURL(file),
        sizeFormatted: formatBytes(file.size)
      }));
      return [...current, ...newItems];
    });
  }, []);

  // System clipboard paste support (Cmd+V / Ctrl+V)
  useEffect(() => {
    function onPaste(event: ClipboardEvent) {
      if (!event.clipboardData) return;
      const items = event.clipboardData.items;
      const pastedFiles: File[] = [];

      for (let i = 0; i < items.length; i++) {
        if (items[i].kind === "file" && items[i].type.startsWith("image/")) {
          const file = items[i].getAsFile();
          if (file) pastedFiles.push(file);
        }
      }

      if (pastedFiles.length > 0) {
        event.preventDefault();
        handleIncomingFiles(pastedFiles);
      }
    }

    window.addEventListener("paste", onPaste);
    return () => window.removeEventListener("paste", onPaste);
  }, [handleIncomingFiles]);

  useEffect(() => {
    return () => {
      imagesRef.current.forEach((img) => URL.revokeObjectURL(img.url));
      cameraStreamRef.current?.getTracks().forEach((track) => track.stop());
    };
  }, []);

  useEffect(() => {
    if (isCameraOpen && videoRef.current && cameraStreamRef.current) {
      videoRef.current.srcObject = cameraStreamRef.current;
    }
  }, [isCameraOpen]);

  function onFileInputChange(event: ChangeEvent<HTMLInputElement>) {
    if (event.target.files && event.target.files.length > 0) {
      handleIncomingFiles(event.target.files);
    }
    event.target.value = "";
  }

  async function openCamera() {
    if (!navigator.mediaDevices?.getUserMedia) {
      cameraInputRef.current?.click();
      return;
    }

    try {
      cameraStreamRef.current = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: "environment" } },
        audio: false
      });
      const track = cameraStreamRef.current.getVideoTracks()[0];
      const capabilities = track.getCapabilities() as MediaTrackCapabilities & {
        zoom?: { min: number; max: number; step: number };
      };
      const settings = track.getSettings() as MediaTrackSettings & { zoom?: number };
      setCameraZoom(capabilities.zoom ? {
        ...capabilities.zoom,
        value: settings.zoom ?? capabilities.zoom.min
      } : null);
      setError("");
      setIsCameraOpen(true);
    } catch {
      setError("Camera access was denied. Allow camera permission and try again.");
    }
  }

  function closeCamera() {
    cameraStreamRef.current?.getTracks().forEach((track) => track.stop());
    cameraStreamRef.current = null;
    setCameraZoom(null);
    setIsCameraOpen(false);
  }

  async function applyCameraZoom(value: number) {
    if (!cameraZoom) return;
    const next = Math.min(cameraZoom.max, Math.max(cameraZoom.min, value));
    const track = cameraStreamRef.current?.getVideoTracks()[0];
    if (!track) return;
    await track.applyConstraints({ advanced: [{ zoom: next } as MediaTrackConstraintSet] });
    setCameraZoom({ ...cameraZoom, value: next });
  }

  function capturePhoto() {
    const video = videoRef.current;
    if (!video || !video.videoWidth || images.length >= MAX_IMAGES) return;

    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext("2d")?.drawImage(video, 0, 0);
    canvas.toBlob((blob) => {
      if (!blob) return;
      handleIncomingFiles([
        new File([blob], `camera-page-${Date.now()}.jpg`, { type: "image/jpeg" })
      ]);
    }, "image/jpeg", 0.92);
  }

  // Dropzone drag-and-drop handlers
  function handleDropzoneDragEnter(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    e.stopPropagation();
    dragCounter.current += 1;
    if (e.dataTransfer.items && e.dataTransfer.items.length > 0) {
      setIsDragOver(true);
    }
  }

  function handleDropzoneDragOver(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    e.stopPropagation();
    e.dataTransfer.dropEffect = "copy";
  }

  function handleDropzoneDragLeave(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    e.stopPropagation();
    dragCounter.current -= 1;
    if (dragCounter.current <= 0) {
      dragCounter.current = 0;
      setIsDragOver(false);
    }
  }

  function handleDropzoneDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    e.stopPropagation();
    dragCounter.current = 0;
    setIsDragOver(false);

    if (draggedCardIndex !== null) return;

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleIncomingFiles(e.dataTransfer.files);
    }
  }

  // Card reordering drag handlers
  function handleCardDragStart(index: number, e: DragEvent<HTMLLIElement>) {
    setDraggedCardIndex(index);
    e.dataTransfer.effectAllowed = "move";
    e.dataTransfer.setData("text/plain", String(index));
  }

  function handleCardDragOver(index: number, e: DragEvent<HTMLLIElement>) {
    e.preventDefault();
    e.stopPropagation();
    e.dataTransfer.dropEffect = "move";
    if (dragOverCardIndex !== index) {
      setDragOverCardIndex(index);
    }
  }

  function handleCardDrop(targetIndex: number, e: DragEvent<HTMLLIElement>) {
    e.preventDefault();
    e.stopPropagation();
    if (draggedCardIndex === null || draggedCardIndex === targetIndex) {
      setDraggedCardIndex(null);
      setDragOverCardIndex(null);
      return;
    }

    setImages((current) => {
      const updated = [...current];
      const [movedItem] = updated.splice(draggedCardIndex, 1);
      updated.splice(targetIndex, 0, movedItem);
      return updated;
    });

    setDraggedCardIndex(null);
    setDragOverCardIndex(null);
  }

  function handleCardDragEnd() {
    setDraggedCardIndex(null);
    setDragOverCardIndex(null);
  }

  function move(index: number, direction: -1 | 1) {
    const nextIndex = index + direction;
    if (nextIndex < 0 || nextIndex >= images.length) return;
    setImages((current) => {
      const next = [...current];
      [next[index], next[nextIndex]] = [next[nextIndex], next[index]];
      return next;
    });
  }

  function remove(id: string) {
    setImages((current) => {
      const removed = current.find((image) => image.id === id);
      if (removed) URL.revokeObjectURL(removed.url);
      return current.filter((image) => image.id !== id);
    });
  }

  function clearAll() {
    if (images.length === 0) return;
    if (window.confirm("Clear all uploaded note images?")) {
      images.forEach((img) => URL.revokeObjectURL(img.url));
      setImages([]);
      setJob(null);
      setExtraction(null);
      setReconstruction(null);
      setCurrentStep("idle");
      setError("");
    }
  }

  // End-to-End Pipeline: Upload -> AI Vision -> Document Reconstruction & PDF Generation
  async function runCompletePipeline() {
    setError("");
    if (images.length < MIN_IMAGES || images.length > MAX_IMAGES) {
      setError(`Please upload between ${MIN_IMAGES} and ${MAX_IMAGES} note images.`);
      return;
    }

    // Step 1: Upload
    setCurrentStep("uploading");
    let createdJob: NoteJob | null = null;
    try {
      createdJob = await createNoteJob(
        images.map((img) => img.file),
        style
      );
      setJob(createdJob);
    } catch (exc) {
      setCurrentStep("idle");
      setError(exc instanceof Error ? exc.message : "Image upload failed.");
      return;
    }

    // Step 2: AI Vision & Layout Analysis
    setCurrentStep("analyzing");
    let extResult: ExtractionResult | null = null;
    try {
      extResult = await analyzeNoteJob(createdJob.job_id);
      setExtraction(extResult);
    } catch (exc) {
      setCurrentStep("idle");
      setError(exc instanceof Error ? exc.message : "Vision analysis failed.");
      return;
    }

    // Step 3: Hierarchical Reconstruction & Deterministic Times New Roman PDF Generation
    setCurrentStep("reconstructing");
    try {
      const recResult = await reconstructNoteJob(createdJob.job_id);
      setReconstruction(recResult);
      setCurrentStep("completed");
      loadLibrary();
    } catch (exc) {
      setCurrentStep("idle");
      setError(exc instanceof Error ? exc.message : "PDF Reconstruction failed.");
    }
  }

  // Fallback direct reconstruction if analysis was already run
  async function triggerReconstructionOnly() {
    if (!job) return;
    setError("");
    setCurrentStep("reconstructing");
    try {
      const recResult = await reconstructNoteJob(job.job_id);
      setReconstruction(recResult);
      setCurrentStep("completed");
      loadLibrary();
    } catch (exc) {
      setCurrentStep("idle");
      setError(exc instanceof Error ? exc.message : "PDF Reconstruction failed.");
    }
  }

  async function handleDeleteLibraryItem(jobId: string) {
    if (!window.confirm("Delete this generated note PDF?")) return;
    try {
      await deleteNoteJob(jobId);
      loadLibrary();
      if (job?.job_id === jobId) {
        setReconstruction(null);
        setJob(null);
      }
    } catch (exc) {
      alert(exc instanceof Error ? exc.message : "Delete failed.");
    }
  }

  return (
    <main className="app-shell">
      {/* Top Navigation & Intro Header */}
      <header className="app-header">
        <button type="button" className="brand" onClick={() => setActiveView("home")} aria-label="MyNotes home">
          <span className="brand-mark" aria-hidden="true">
            <svg viewBox="0 0 32 38" fill="none" stroke="currentColor" strokeWidth="1.8">
              <rect x="4" y="2" width="24" height="34" rx="2" />
              <path d="M9 10h14M9 16h14M9 22h14M9 28h10" />
            </svg>
          </span>
          <span>MyNotes</span>
        </button>

        <nav className="main-nav" aria-label="Primary navigation">
          <button type="button" className={`nav-link ${activeView === "home" ? "nav-link-active" : ""}`} aria-current={activeView === "home" ? "page" : undefined} onClick={() => setActiveView("home")}>Home</button>
          <button
            type="button"
            className="nav-link"
            onClick={() => setIsLibraryOpen(true)}
          >
            My Notes
          </button>
          <button type="button" className={`nav-link ${activeView === "about" ? "nav-link-active" : ""}`} aria-current={activeView === "about" ? "page" : undefined} onClick={() => setActiveView("about")}>About</button>
        </nav>
      </header>

      {activeView === "home" && <section className="intro" id="home">
        <p className="hero-copy">
          Upload your lecture note images and get clean, structured PDFs<br />
          with text, formulas, and diagrams — just like your own handwriting.
        </p>
      </section>}

      {/* Main Unified Workspace */}
      <section className={`unified-upload-workspace ${activeView === "about" ? "workspace-about" : ""}`}>
        <input
          ref={fileInputRef}
          accept="image/*"
          multiple
          type="file"
          className="visually-hidden"
          hidden
          id="unified-file-input"
          onChange={onFileInputChange}
        />
        <input
          ref={cameraInputRef}
          accept="image/*"
          capture="environment"
          type="file"
          className="visually-hidden"
          hidden
          id="camera-file-input"
          onChange={onFileInputChange}
        />

        <div className="upload-actions">
        {/* Primary Dropzone */}
        <div
          className={`dropzone-container ${images.length > 0 ? "dropzone-compact" : "dropzone-hero"} ${
            isDragOver ? "dropzone-active" : ""
          }`}
          onDragEnter={handleDropzoneDragEnter}
          onDragOver={handleDropzoneDragOver}
          onDragLeave={handleDropzoneDragLeave}
          onDrop={handleDropzoneDrop}
          onClick={() => fileInputRef.current?.click()}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              fileInputRef.current?.click();
            }
          }}
          aria-label="Upload note images by dropping files or clicking to browse"
        >
          <div className="dropzone-icon-wrap">
            <svg
              className="dropzone-icon"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.75"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M4 14.899A7 7 0 1 1 15.71 8h1.79a4.5 4.5 0 0 1 2.5 8.242" />
              <path d="M12 12v9" />
              <path d="m16 16-4-4-4 4" />
            </svg>
          </div>

          <div className="dropzone-text">
            <h2 className="dropzone-title">
              {isDragOver ? "Drop note images here" : "Drag and drop"}
            </h2>
            <p className="dropzone-subtitle">
              or <span className="browse-link">browse files</span> from your computer
            </p>
            <div className="dropzone-meta">
              <span>Supports JPG, PNG, WEBP, HEIC</span>
            </div>
          </div>
        </div>

        <button
          type="button"
          className="btn-camera capture-launch"
          onClick={openCamera}
          disabled={images.length >= MAX_IMAGES || (currentStep !== "idle" && currentStep !== "completed")}
          title={images.length >= MAX_IMAGES ? "Maximum 100 pages reached" : "Take a photo of your notes"}
        >
          <svg viewBox="0 0 24 24" width="34" height="34" fill="none" stroke="currentColor" strokeWidth="1.75" aria-hidden="true">
            <path d="M14.5 4 16 7h3a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V9a2 2 0 0 1 2-2h3l1.5-3z" />
            <circle cx="12" cy="13" r="3" />
          </svg>
          <strong>Capture image</strong>
          <span>Use your device’s camera to take a photo</span>
        </button>
        </div>
        <span className="upload-requirement">1 to 100 pages required</span>

        {/* Controls & Batch Progress Bar */}
        <div className="action-bar">
          <div className="progress-section">
            <div className="progress-labels">
              <span className="count-tag">
                <strong>{images.length}</strong> pages added
              </span>
              <span className={`status-tag ${isValidCount ? "status-tag-valid" : "status-tag-pending"}`}>
                {countStatus}
              </span>
            </div>
            <div className="progress-bar-track" aria-hidden="true">
              <div
                className={`progress-bar-fill ${isValidCount ? "fill-valid" : ""}`}
                style={{ width: `${progressPercentage}%` }}
              />
            </div>
          </div>

          <div className="controls-section">
            <label className="style-select-label">
              <span>PDF Style</span>
              <select
                value={style}
                onChange={(e) => setStyle(e.target.value)}
                disabled={currentStep !== "idle" && currentStep !== "completed"}
                className="style-dropdown"
              >
                <option value="notebook">Notebook Style</option>
                <option value="clean">Clean Minimalist</option>
              </select>
            </label>

            {images.length > 0 && (
              <button
                type="button"
                className="btn-secondary"
                onClick={clearAll}
                disabled={currentStep !== "idle" && currentStep !== "completed"}
                title="Remove all images"
              >
                Clear all
              </button>
            )}

            <button
              type="button"
              className="btn-primary"
              disabled={!isValidCount || (currentStep !== "idle" && currentStep !== "completed")}
              onClick={runCompletePipeline}
            >
              {currentStep === "uploading" && (
                <>
                  <span className="spinner" />
                  Uploading...
                </>
              )}
              {currentStep === "analyzing" && (
                <>
                  <span className="spinner" />
                  Analyzing Notes...
                </>
              )}
              {currentStep === "reconstructing" && (
                <>
                  <span className="spinner" />
                  Rendering PDF...
                </>
              )}
              {currentStep === "completed" && "Regenerate PDF"}
              {currentStep === "idle" && "Generate Notes & PDF"}
            </button>
          </div>
        </div>

        {activeView === "about" && (
          <section className="benefits" id="about" aria-label="Why MyNotes">
            <article>
              <span className="benefit-icon benefit-icon-green" aria-hidden="true">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M6 2h9l4 4v16H6z"/><path d="M14 2v5h5M9 12h7M9 16h7"/></svg>
              </span>
              <h3>Clean &amp; Structured</h3>
              <p>Organized notes with clear<br />headings and formatting</p>
            </article>
            <article>
              <span className="benefit-icon benefit-icon-bronze" aria-hidden="true">Σ</span>
              <h3>Preserves Content</h3>
              <p>Keeps formulas, diagrams,<br />tables and images</p>
            </article>
            <article>
              <span className="benefit-icon benefit-icon-green" aria-hidden="true">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M12 2 4 5v6c0 5.2 3.4 9 8 11 4.6-2 8-5.8 8-11V5z"/><path d="m8.5 12 2.2 2.2 4.8-5"/></svg>
              </span>
              <h3>Your Data, Your Control</h3>
              <p>Images are used only to create<br />your PDF and then deleted</p>
            </article>
            <article>
              <span className="benefit-icon benefit-icon-bronze" aria-hidden="true">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="m13 2-8 12h7l-1 8 8-12h-7z"/></svg>
              </span>
              <h3>Fast &amp; Reliable</h3>
              <p>Get high-quality notes<br />in minutes</p>
            </article>
          </section>
        )}

        {/* 4-Stage Active Pipeline Stepper */}
        {currentStep !== "idle" && (
          <div className="stepper-banner">
            <div className={`step-item ${currentStep === "uploading" ? "step-active" : "step-done"}`}>
              <div className="step-circle">1</div>
              <span>Upload ({images.length} files)</span>
            </div>
            <div className="step-connector" />
            <div
              className={`step-item ${
                currentStep === "analyzing"
                  ? "step-active"
                  : currentStep === "reconstructing" || currentStep === "completed"
                  ? "step-done"
                  : "step-pending"
              }`}
            >
              <div className="step-circle">2</div>
              <span>Vision Extraction</span>
            </div>
            <div className="step-connector" />
            <div
              className={`step-item ${
                currentStep === "reconstructing"
                  ? "step-active"
                  : currentStep === "completed"
                  ? "step-done"
                  : "step-pending"
              }`}
            >
              <div className="step-circle">3</div>
              <span>Hierarchical PDF Render</span>
            </div>
            <div className="step-connector" />
            <div className={`step-item ${currentStep === "completed" ? "step-active step-done" : "step-pending"}`}>
              <div className="step-circle">4</div>
              <span>Ready</span>
            </div>
          </div>
        )}

        {/* Error message */}
        {error && (
          <div className="alert-box alert-error" role="alert">
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
            <div className="alert-content">
              <span>{error}</span>
              {job && extraction && !reconstruction && (
                <button type="button" className="btn-inline-retry" onClick={triggerReconstructionOnly}>
                  Build PDF
                </button>
              )}
            </div>
          </div>
        )}

        {/* COMPLETED PDF RESULT CARD */}
        {reconstruction && (
          <div className="pdf-result-card">
            <div className="pdf-result-header">
              <div className="pdf-badge-icon">
                <svg viewBox="0 0 24 24" width="28" height="28" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <polyline points="14 2 14 8 20 8" />
                  <line x1="16" y1="13" x2="8" y2="13" />
                  <line x1="16" y1="17" x2="8" y2="17" />
                  <polyline points="10 9 9 9 8 9" />
                </svg>
              </div>
              <div className="pdf-result-meta">
                <span className="pdf-pill-success">Reconstruction Complete</span>
                <h2>{reconstruction.title}</h2>
                <div className="pdf-details-row">
                  <span>{reconstruction.page_count} PDF pages</span>
                  <span>•</span>
                  <span>Times New Roman Typography</span>
                  <span>•</span>
                  <span>{style === "notebook" ? "Notebook Style" : "Clean Publication"}</span>
                </div>
              </div>
            </div>

            <div className="pdf-result-actions">
              <button
                type="button"
                className="btn-preview-pdf"
                onClick={() => setActivePdfModalJobId(reconstruction.job_id)}
              >
                <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                  <circle cx="12" cy="12" r="3" />
                </svg>
                Preview PDF
              </button>

              <a
                href={getPdfDownloadUrl(reconstruction.job_id)}
                download
                className="btn-download-pdf"
              >
                <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                  <polyline points="7 10 12 15 17 10" />
                  <line x1="12" y1="15" x2="12" y2="3" />
                </svg>
                Download PDF
              </a>
              <a
                href={getDocxDownloadUrl(reconstruction.job_id)}
                download
                className="btn-download-pdf"
              >
                Download DOCX
              </a>
            </div>

            {/* Document Structure Accordion */}
            <div className="hierarchy-accordion">
              <button
                type="button"
                className="hierarchy-toggle-btn"
                onClick={() => setIsExpandedHierarchy(!isExpandedHierarchy)}
              >
                <span>
                  Reconstructed Document Hierarchy ({reconstruction.document.sections.length} Sections,{" "}
                  {reconstruction.document.total_elements} Elements)
                </span>
                <span>{isExpandedHierarchy ? "▲ Hide" : "▼ View Structure"}</span>
              </button>

              {isExpandedHierarchy && (
                <div className="hierarchy-content">
                  {reconstruction.document.sections.map((sec, sIdx) => (
                    <div key={sIdx} className="hierarchy-section-item">
                      <div className="section-title">
                        <strong>Section {sIdx + 1}:</strong> {sec.main_title}
                      </div>
                      <ul className="section-elements-list">
                        {sec.elements.map((el, elIdx) => (
                          <li key={elIdx} className="element-chip">
                            <span className={`chip-type type-${el.type}`}>{el.type}</span>
                            <span className="chip-text">
                              {el.text || (el.image_id ? `Visual (${el.image_id})` : "Element")}
                            </span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Gallery / Reorder Grid */}
        {images.length > 0 && (
          <div className="gallery-container">
            <div className="gallery-header">
              <h3>
                Page Sequence ({images.length} {images.length === 1 ? "page" : "pages"})
              </h3>
              <p className="gallery-tip">
                Drag cards to reorder note pages. The final PDF is reconstructed strictly in this order.
              </p>
            </div>

            <ol className="preview-grid" aria-label="Selected note page order">
              {images.map((image, index) => {
                const isItemDragged = draggedCardIndex === index;
                const isItemDropTarget = dragOverCardIndex === index;

                return (
                  <li
                    key={image.id}
                    className={`preview-card ${isItemDragged ? "card-dragging" : ""} ${
                      isItemDropTarget ? "card-drop-target" : ""
                    }`}
                    draggable
                    onDragStart={(e) => handleCardDragStart(index, e)}
                    onDragOver={(e) => handleCardDragOver(index, e)}
                    onDrop={(e) => handleCardDrop(index, e)}
                    onDragEnd={handleCardDragEnd}
                  >
                    <div className="card-media-wrapper">
                      <img src={image.url} alt={`Note page ${index + 1}`} loading="lazy" />
                      <div className="card-badge">Page {String(index + 1).padStart(2, "0")}</div>
                      <button
                        type="button"
                        className="card-zoom-btn"
                        onClick={() => setPreviewModalImage(image)}
                        title="Click to view full image"
                        aria-label={`Zoom page ${index + 1}`}
                      >
                        <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="2">
                          <circle cx="11" cy="11" r="8" />
                          <line x1="21" y1="21" x2="16.65" y2="16.65" />
                          <line x1="11" y1="8" x2="11" y2="14" />
                          <line x1="8" y1="11" x2="14" y2="11" />
                        </svg>
                      </button>
                    </div>

                    <div className="card-info">
                      <span className="card-filename" title={image.file.name}>
                        {image.file.name}
                      </span>
                      <span className="card-size">{image.sizeFormatted}</span>
                    </div>

                    <div className="card-actions">
                      <div className="card-shift-group">
                        <button
                          type="button"
                          className="btn-icon"
                          onClick={() => move(index, -1)}
                          disabled={index === 0}
                          title="Move earlier"
                          aria-label={`Move page ${index + 1} earlier`}
                        >
                          ↑
                        </button>
                        <button
                          type="button"
                          className="btn-icon"
                          onClick={() => move(index, 1)}
                          disabled={index === images.length - 1}
                          title="Move later"
                          aria-label={`Move page ${index + 1} later`}
                        >
                          ↓
                        </button>
                      </div>

                      <button
                        type="button"
                        className="btn-card-remove"
                        onClick={() => remove(image.id)}
                        title="Remove page"
                        aria-label={`Remove page ${index + 1}`}
                      >
                        <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2">
                          <line x1="18" y1="6" x2="6" y2="18" />
                          <line x1="6" y1="6" x2="18" y2="18" />
                        </svg>
                      </button>
                    </div>
                  </li>
                );
              })}

              {/* Inline "Add more" drop target card */}
              <li
                className={`add-more-card ${isDragOver ? "dropzone-active" : ""}`}
                onClick={() => fileInputRef.current?.click()}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    fileInputRef.current?.click();
                  }
                }}
                aria-label="Add more pages"
              >
                <div className="add-more-content">
                  <svg viewBox="0 0 24 24" width="28" height="28" fill="none" stroke="currentColor" strokeWidth="2">
                    <line x1="12" y1="5" x2="12" y2="19" />
                    <line x1="5" y1="12" x2="19" y2="12" />
                  </svg>
                  <span>Add More Pages</span>
                  <small>Drop files or click</small>
                </div>
              </li>
            </ol>
          </div>
        )}
      </section>

      {isCameraOpen && (
        <div className="modal-backdrop" onClick={closeCamera}>
          <div className="modal-dialog camera-dialog" onClick={(event) => event.stopPropagation()}>
            <div className="modal-header">
              <div className="modal-title">
                <strong>Capture note pages</strong>
                <span>{images.length} of {MAX_IMAGES} pages</span>
              </div>
              <button type="button" className="modal-close-btn" onClick={closeCamera} aria-label="Close camera">
                ✕
              </button>
            </div>
            <div className="camera-preview">
              <video ref={videoRef} autoPlay playsInline muted />
            </div>
            <div className="camera-controls">
              {cameraZoom && (
                <div className="camera-zoom">
                  <button type="button" onClick={() => applyCameraZoom(cameraZoom.value - cameraZoom.step)} aria-label="Zoom out">−</button>
                  <input
                    type="range"
                    min={cameraZoom.min}
                    max={cameraZoom.max}
                    step={cameraZoom.step}
                    value={cameraZoom.value}
                    onChange={(event) => applyCameraZoom(Number(event.target.value))}
                    aria-label="Camera zoom"
                  />
                  <button type="button" onClick={() => applyCameraZoom(cameraZoom.value + cameraZoom.step)} aria-label="Zoom in">+</button>
                  <span>{cameraZoom.value.toFixed(1)}×</span>
                </div>
              )}
              <button
                type="button"
                className="camera-shutter"
                onClick={capturePhoto}
                disabled={images.length >= MAX_IMAGES}
                aria-label="Take photo"
              />
              <span>{images.length >= MAX_IMAGES ? "Maximum 100 pages reached" : "Tap to capture a page"}</span>
            </div>
          </div>
        </div>
      )}

      {/* MODAL 1: Image Zoom Modal */}
      {previewModalImage && (
        <div className="modal-backdrop" onClick={() => setPreviewModalImage(null)}>
          <div className="modal-dialog" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div className="modal-title">
                <strong>{previewModalImage.file.name}</strong>
                <span>{previewModalImage.sizeFormatted}</span>
              </div>
              <button
                type="button"
                className="modal-close-btn"
                onClick={() => setPreviewModalImage(null)}
                aria-label="Close preview"
              >
                ✕
              </button>
            </div>
            <div className="modal-body">
              <img src={previewModalImage.url} alt={previewModalImage.file.name} />
            </div>
          </div>
        </div>
      )}

      {/* MODAL 2: Inline PDF Viewer Modal */}
      {activePdfModalJobId && (
        <div className="modal-backdrop" onClick={() => setActivePdfModalJobId(null)}>
          <div className="modal-dialog modal-pdf-dialog" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div className="modal-title">
                <strong>Generated PDF Preview</strong>
                <span>Times New Roman Format</span>
              </div>
              <div className="modal-header-actions">
                <a
                  href={getPdfDownloadUrl(activePdfModalJobId)}
                  download
                  className="btn-modal-download"
                >
                  Download PDF
                </a>
                <button
                  type="button"
                  className="modal-close-btn"
                  onClick={() => setActivePdfModalJobId(null)}
                  aria-label="Close PDF viewer"
                >
                  ✕
                </button>
              </div>
            </div>
            <div className="modal-pdf-body">
              <iframe
                src={getPdfViewUrl(activePdfModalJobId)}
                title="Generated PDF Viewer"
                className="pdf-iframe"
              />
            </div>
          </div>
        </div>
      )}

      {/* DRAWER: Notes Library Drawer */}
      {isLibraryOpen && (
        <div className="drawer-backdrop" onClick={() => setIsLibraryOpen(false)}>
          <aside className="drawer-panel" onClick={(e) => e.stopPropagation()}>
            <div className="drawer-header">
              <div className="drawer-title">
                <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
                  <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
                </svg>
                <h3>Notes Library</h3>
              </div>
              <button
                type="button"
                className="drawer-close-btn"
                onClick={() => setIsLibraryOpen(false)}
                aria-label="Close library"
              >
                ✕
              </button>
            </div>

            <div className="drawer-body">
              {libraryItems.length === 0 ? (
                <div className="drawer-empty">No generated notes yet. Generate your first batch!</div>
              ) : (
                <ul className="library-list">
                  {libraryItems.map((item) => (
                    <li key={item.job_id} className="library-card">
                      <div className="library-card-info">
                        <strong>{item.title}</strong>
                        <div className="library-card-meta">
                          <span>{item.image_count} source photos</span>
                          {item.page_count && <span>• {item.page_count} PDF pages</span>}
                          <span>• {new Date(item.created_at).toLocaleDateString()}</span>
                        </div>
                        <span className={`lib-status-badge status-${item.status.toLowerCase()}`}>
                          {item.status}
                        </span>
                      </div>

                      <div className="library-card-actions">
                        {item.status === "COMPLETED" && (
                          <>
                            <button
                              type="button"
                              className="btn-lib-action"
                              onClick={() => {
                                setIsLibraryOpen(false);
                                setActivePdfModalJobId(item.job_id);
                              }}
                            >
                              Preview
                            </button>
                            <a
                              href={getPdfDownloadUrl(item.job_id)}
                              download
                              className="btn-lib-action btn-lib-download"
                            >
                              PDF
                            </a>
                            <a
                              href={getDocxDownloadUrl(item.job_id)}
                              download
                              className="btn-lib-action btn-lib-download"
                            >
                              DOCX
                            </a>
                          </>
                        )}
                        <button
                          type="button"
                          className="btn-lib-delete"
                          onClick={() => handleDeleteLibraryItem(item.job_id)}
                          disabled={!(["UPLOADED", "COMPLETED", "FAILED", "CLEANED"].includes(item.status))}
                          title={(["UPLOADED", "COMPLETED", "FAILED", "CLEANED"].includes(item.status)) ? "Delete note" : "Wait for processing to finish"}
                        >
                          ✕
                        </button>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </aside>
        </div>
      )}
    </main>
  );
}
