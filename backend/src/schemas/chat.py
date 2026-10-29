from pydantic import BaseModel, Field


class ConversationCreate(BaseModel):
    title: str | None = None
    selected_document_ids: list[str] = Field(default_factory=list)


class ConversationUpdate(BaseModel):
    title: str | None = None
    selected_document_ids: list[str] | None = None
    archived: bool | None = None


class ConversationResponse(BaseModel):
    id: str
    title: str
    selected_document_ids: list[str]
    archived: bool
    created_at: str
    updated_at: str


class CitationResponse(BaseModel):
    id: str
    message_id: str
    label: str
    document_id: str
    chunk_id: str | None
    generation: int
    filename: str
    source_type: str | None
    locator: dict
    excerpt: str | None


class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    status: str
    model_id: str | None = None
    latency_ms: int | None = None
    created_at: str
    citations: list[CitationResponse] = Field(default_factory=list)


class ChatRequest(BaseModel):
    conversation_id: str
    message: str
    idempotency_key: str | None = None
    selected_document_ids: list[str] | None = None


class RegenerateRequest(BaseModel):
    conversation_id: str
    message_id: str | None = None  # last user message if omitted
