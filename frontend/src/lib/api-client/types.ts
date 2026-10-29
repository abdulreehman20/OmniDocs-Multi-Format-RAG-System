export type DocumentRecord = {
  id: string;
  filename: string;
  source_type: string;
  mime_type: string;
  byte_size: number;
  status: string;
  ingestion_stage: string | null;
  ingestion_progress: number | null;
  error_code: string | null;
  error_message: string | null;
  status_message: string | null;
  created_at: string;
  updated_at: string;
};

export type UploadLimits = {
  max_file_size_bytes: number;
  max_files_per_selection: number;
  accepted_extensions: string;
};

export type UploadInitResponse = {
  document_id: string;
  upload_session_id: string;
  status: string;
  put_url: string | null;
  object_key: string;
  expires_seconds: number;
};

export type ConversationRecord = {
  id: string;
  title: string;
  selected_document_ids: string[];
  archived: boolean;
  created_at: string;
  updated_at: string;
};

export type CitationRecord = {
  id: string;
  message_id: string;
  label: string;
  document_id: string;
  chunk_id: string | null;
  generation: number;
  filename: string;
  source_type: string | null;
  locator: Record<string, unknown>;
  excerpt: string | null;
};

export type MessageRecord = {
  id: string;
  conversation_id: string;
  role: string;
  content: string;
  status: string;
  model_id: string | null;
  latency_ms: number | null;
  created_at: string;
  citations: CitationRecord[];
};
