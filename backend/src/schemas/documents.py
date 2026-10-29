from pydantic import BaseModel, Field


class UploadInitRequest(BaseModel):
    filename: str
    mime_type: str = ""
    byte_size: int
    idempotency_key: str = Field(min_length=8, max_length=128)
    client_checksum: str | None = None


class UploadInitResponse(BaseModel):
    document_id: str
    upload_session_id: str
    status: str
    put_url: str | None
    object_key: str
    expires_seconds: int


class DocumentResponse(BaseModel):
    id: str
    filename: str
    source_type: str
    mime_type: str
    byte_size: int
    status: str
    ingestion_stage: str | None = None
    ingestion_progress: float | None = None
    error_code: str | None = None
    error_message: str | None = None
    status_message: str | None = None
    created_at: str
    updated_at: str


class DownloadResponse(BaseModel):
    document_id: str
    filename: str
    download_url: str
    expires_seconds: int


class LimitsResponse(BaseModel):
    max_file_size_bytes: int
    max_files_per_selection: int
    accepted_extensions: str


class IngestionJobResponse(BaseModel):
    id: str
    document_id: str
    generation: int
    status: str
    stage: str
    attempts: int
    error_code: str | None = None
    error_message: str | None = None
    progress: dict = {}
    started_at: str | None = None
    finished_at: str | None = None
    created_at: str

