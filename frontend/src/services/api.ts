import type { ExtractionResult, NoteJob, NoteListItem, ReconstructionResponse } from "../types/note";

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

export async function createNoteJob(files: File[], style: string): Promise<NoteJob> {
  const form = new FormData();
  files.forEach((file) => form.append("files", file));
  form.append("style", style);

  const response = await fetch(`${API_BASE}/api/v1/notes`, {
    method: "POST",
    body: form,
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? "Upload failed.");
  }

  return response.json();
}

export async function analyzeNoteJob(jobId: string): Promise<ExtractionResult> {
  const response = await fetch(`${API_BASE}/api/v1/notes/${jobId}/analyze`, {
    method: "POST",
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? "Analysis failed.");
  }

  return response.json();
}

export async function reconstructNoteJob(jobId: string): Promise<ReconstructionResponse> {
  const response = await fetch(`${API_BASE}/api/v1/notes/${jobId}/reconstruct`, {
    method: "POST",
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? "PDF Reconstruction failed.");
  }

  return response.json();
}

export async function fetchNotesLibrary(): Promise<NoteListItem[]> {
  const response = await fetch(`${API_BASE}/api/v1/notes`);
  if (!response.ok) {
    throw new Error("Failed to load notes library.");
  }
  return response.json();
}

export function getPdfViewUrl(jobId: string): string {
  return `${API_BASE}/api/v1/notes/${jobId}/pdf`;
}

export function getPdfDownloadUrl(jobId: string): string {
  return `${API_BASE}/api/v1/notes/${jobId}/download`;
}

export function getDocxDownloadUrl(jobId: string): string {
  return `${API_BASE}/api/v1/notes/${jobId}/docx`;
}

export async function deleteNoteJob(jobId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/api/v1/notes/${jobId}`, {
    method: "DELETE",
  });
  if (!response.ok) {
    throw new Error("Failed to delete note.");
  }
}
