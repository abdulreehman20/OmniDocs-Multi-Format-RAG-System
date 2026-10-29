from src.ai.rag.citations import extract_citation_labels, validate_citations
from src.ai.rag.types import RetrievedSource


def _src(label: str) -> RetrievedSource:
    return RetrievedSource(
        label=label,
        chunk_id=f"chunk-{label}",
        vector_id=f"vec-{label}",
        document_id="doc-1",
        owner_id="user-a",
        generation=1,
        filename="notes.md",
        source_type="markdown",
        locator={"heading": "Intro"},
        text="hello",
        score=0.9,
    )


def test_extract_citation_labels_ordered_unique():
    text = "A [S1] and [S2] then [S1] again and invented [S9]."
    assert extract_citation_labels(text) == ["S1", "S2", "S9"]


def test_validate_citations_drops_invented_labels():
    sources = [_src("S1"), _src("S2")]
    answer = "Fact [S1]. Hallucination [S99]. Also [S2]."
    valid = validate_citations(answer, sources)
    assert [s.label for s in valid] == ["S1", "S2"]
