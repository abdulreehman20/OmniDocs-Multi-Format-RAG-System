from pathlib import Path

import pytest
from src.ai.ingestion.chunking import chunk_extracted
from src.ai.ingestion.normalize import normalize_extracted
from src.ai.ingestion.pipeline import build_vector_id, parse_local_file
from src.ai.ingestion.registry import IngestionParseError, load_document
from src.config import get_settings


@pytest.fixture()
def settings():
    get_settings.cache_clear()
    return get_settings()


def test_build_vector_id_deterministic() -> None:
    assert build_vector_id("doc-1", 2, 3) == "doc-1:2:3"


def test_load_markdown_and_chunk(tmp_path: Path, settings) -> None:
    path = tmp_path / "note.md"
    path.write_text("# Title\n\nHello world.\n\n## Section\n\nMore text here.", encoding="utf-8")
    extracted = load_document(path, source_type="markdown", settings=settings)
    assert extracted.units
    normalized = normalize_extracted(extracted)
    chunks = chunk_extracted(
        normalized,
        source_type="markdown",
        settings=settings,
        generation=1,
        embedding_model_id=settings.embedding_model_id,
    )
    assert chunks
    assert chunks[0].text_sha256
    assert chunks[0].chunk_index == 0


def test_load_csv_keeps_header_chunks(tmp_path: Path, settings) -> None:
    path = tmp_path / "rows.csv"
    path.write_text("name,age\nalice,30\nbob,40\ncarol,50\n", encoding="utf-8")
    units, chunks, _ = parse_local_file(
        path,
        source_type="csv",
        settings=settings,
        generation=1,
        embedding_model_id="test-model",
    )
    assert units
    assert chunks
    assert "name" in chunks[0].text.lower() or "alice" in chunks[0].text.lower()


def test_empty_pdf_fails(tmp_path: Path, settings) -> None:
    # Minimal invalid/empty-ish pdf bytes that pypdf may open but with no text,
    # or fail parse — either IngestionParseError is acceptable.
    path = tmp_path / "blank.pdf"
    path.write_bytes(
        b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"
    )
    with pytest.raises(IngestionParseError):
        load_document(path, source_type="pdf", settings=settings)


def test_chunk_indexes_are_stable(tmp_path: Path, settings) -> None:
    path = tmp_path / "a.txt"
    path.write_text("alpha\n\n" * 40, encoding="utf-8")
    _, chunks_a, _ = parse_local_file(
        path,
        source_type="text",
        settings=settings,
        generation=1,
        embedding_model_id="m",
    )
    _, chunks_b, _ = parse_local_file(
        path,
        source_type="text",
        settings=settings,
        generation=1,
        embedding_model_id="m",
    )
    assert [c.text_sha256 for c in chunks_a] == [c.text_sha256 for c in chunks_b]
    assert [c.chunk_index for c in chunks_a] == list(range(len(chunks_a)))
