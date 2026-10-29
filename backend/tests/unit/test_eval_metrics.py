from src.ai.rag.types import RetrievedSource
from src.evals.metrics import abstention_quality, citation_validity_score


def test_citation_validity_drops_invented():
    sources = [
        RetrievedSource(
            label="S1",
            chunk_id="c1",
            vector_id="v1",
            document_id="d1",
            owner_id="u",
            generation=1,
            filename="a.md",
            source_type="markdown",
            locator={},
            text="x",
            score=1.0,
        )
    ]
    assert citation_validity_score("Fact [S1] and [S9]", sources) == 0.5


def test_abstention_for_unanswerable():
    assert (
        abstention_quality(
            answerable=False,
            answer="I couldn't find enough information in the selected documents.",
        )
        == 1.0
    )
    assert abstention_quality(answerable=False, answer="The answer is 42.") == 0.0
