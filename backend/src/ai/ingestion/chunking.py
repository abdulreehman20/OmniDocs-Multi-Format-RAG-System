import hashlib

from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.ai.ingestion.contracts import ChunkUnit, ExtractedDocument
from src.config import Settings
from src.db.models import DocumentSourceType


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _token_estimate(text: str) -> int:
    # ponytail: ~4 chars/token heuristic; upgrade to tiktoken encode if metering needs accuracy
    return max(1, len(text) // 4)


def _splitter_for(source_type: str, settings: Settings) -> RecursiveCharacterTextSplitter:
    if source_type == DocumentSourceType.MARKDOWN:
        return RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size_markdown,
            chunk_overlap=settings.chunk_overlap_markdown,
            separators=["\n## ", "\n### ", "\n\n", "\n", " ", ""],
        )
    if source_type == DocumentSourceType.PDF:
        return RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size_pdf,
            chunk_overlap=settings.chunk_overlap_pdf,
            separators=["\n\n", "\n", " ", ""],
        )
    if source_type == DocumentSourceType.DOCX:
        return RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size_docx,
            chunk_overlap=settings.chunk_overlap_docx,
            separators=["\n\n", "\n", " ", ""],
        )
    return RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size_text,
        chunk_overlap=settings.chunk_overlap_text,
        separators=["\n\n", "\n", " ", ""],
    )


def _chunk_csv(
    doc: ExtractedDocument,
    *,
    settings: Settings,
    generation: int,
    embedding_model_id: str,
) -> list[ChunkUnit]:
    rows = [u for u in doc.units if u.text]
    if not rows:
        return []
    header = rows[0].text
    body = rows[1:] if len(rows) > 1 else []
    size = max(1, settings.csv_rows_per_chunk)
    chunks: list[ChunkUnit] = []
    idx = 0
    for start in range(0, len(body), size):
        group = body[start : start + size]
        text = header + "\n" + "\n".join(u.text for u in group)
        locator = {
            "row_start": start + 1,
            "row_end": start + len(group),
            "kind": "csv_rows",
        }
        chunks.append(
            ChunkUnit(
                chunk_index=idx,
                text=text,
                text_sha256=_sha256(text),
                token_estimate=_token_estimate(text),
                locator=locator,
                chunker_version=settings.chunker_version,
                embedding_model_id=embedding_model_id,
                generation=generation,
            )
        )
        idx += 1
    if not body:
        text = header
        chunks.append(
            ChunkUnit(
                chunk_index=0,
                text=text,
                text_sha256=_sha256(text),
                token_estimate=_token_estimate(text),
                locator={"row_start": 0, "row_end": 0, "kind": "csv_header_only"},
                chunker_version=settings.chunker_version,
                embedding_model_id=embedding_model_id,
                generation=generation,
            )
        )
    return chunks


def chunk_extracted(
    doc: ExtractedDocument,
    *,
    source_type: str,
    settings: Settings,
    generation: int,
    embedding_model_id: str,
) -> list[ChunkUnit]:
    if source_type == DocumentSourceType.CSV:
        return _chunk_csv(
            doc,
            settings=settings,
            generation=generation,
            embedding_model_id=embedding_model_id,
        )

    splitter = _splitter_for(source_type, settings)
    chunks: list[ChunkUnit] = []
    idx = 0
    for unit in doc.units:
        parts = splitter.split_text(unit.text)
        for part in parts:
            part = part.strip()
            if not part:
                continue
            locator = dict(unit.locator)
            locator["kind"] = source_type
            chunks.append(
                ChunkUnit(
                    chunk_index=idx,
                    text=part,
                    text_sha256=_sha256(part),
                    token_estimate=_token_estimate(part),
                    locator=locator,
                    chunker_version=settings.chunker_version,
                    embedding_model_id=embedding_model_id,
                    generation=generation,
                )
            )
            idx += 1
    return chunks
