from src.db.models import DocumentSourceType

# extension -> (source_type, allowed mime prefixes/exact)
ALLOWED_UPLOADS: dict[str, tuple[DocumentSourceType, frozenset[str]]] = {
    ".md": (DocumentSourceType.MARKDOWN, frozenset({"text/markdown", "text/plain"})),
    ".markdown": (DocumentSourceType.MARKDOWN, frozenset({"text/markdown", "text/plain"})),
    ".txt": (DocumentSourceType.TEXT, frozenset({"text/plain"})),
    ".pdf": (DocumentSourceType.PDF, frozenset({"application/pdf"})),
    ".csv": (DocumentSourceType.CSV, frozenset({"text/csv", "application/csv", "text/plain"})),
    ".docx": (
        DocumentSourceType.DOCX,
        frozenset(
            {
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "application/octet-stream",
            }
        ),
    ),
}


def resolve_upload_type(filename: str, mime_type: str) -> tuple[DocumentSourceType, str]:
    name = filename.rsplit("/", 1)[-1]
    if "." not in name:
        raise ValueError("unsupported_file_type")
    ext = "." + name.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_UPLOADS:
        raise ValueError("unsupported_file_type")
    source_type, allowed_mimes = ALLOWED_UPLOADS[ext]
    normalized_mime = (mime_type or "").split(";")[0].strip().lower()
    if normalized_mime and normalized_mime not in allowed_mimes:
        raise ValueError("unsupported_mime_type")
    # Prefer a canonical mime when client sends empty
    canonical = next(iter(allowed_mimes))
    return source_type, normalized_mime or canonical


def accept_attribute() -> str:
    return ",".join(ALLOWED_UPLOADS.keys())
