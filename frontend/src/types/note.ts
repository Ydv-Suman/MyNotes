export type NoteJob = {
  job_id: string;
  status: string;
  title: string;
  image_count: number;
  page_count?: number | null;
  style?: string | null;
  completed_at?: string | null;
};

export type DocumentElement = {
  type: string;
  text?: string | null;
  image_id?: string | null;
  confidence?: number | null;
  children: DocumentElement[];
  data: Record<string, unknown>;
};

export type PageExtraction = {
  image_number: number;
  source_name: string;
  main_title?: string | null;
  elements: DocumentElement[];
};

export type ExtractionResult = {
  job_id: string;
  pages: PageExtraction[];
};

export type DocumentSection = {
  main_title: string;
  elements: DocumentElement[];
};

export type ReconstructedDocument = {
  job_id: string;
  title: string;
  sections: DocumentSection[];
  total_elements: number;
};

export type ReconstructionResponse = {
  job_id: string;
  status: string;
  title: string;
  page_count: number;
  pdf_url: string;
  download_url: string;
  docx_download_url: string;
  document: ReconstructedDocument;
};

export type NoteListItem = {
  job_id: string;
  title: string;
  status: string;
  image_count: number;
  page_count?: number | null;
  style?: string | null;
  created_at: string;
  completed_at?: string | null;
};
