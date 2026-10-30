from src.ai.rag.generation import stream_answer_tokens
from src.config import Settings


def test_abstention_when_no_sources():
    settings = Settings(
        database_url="sqlite://",
        database_url_pooled="sqlite://",
        neon_auth_base_url="https://auth.example.neon.tech/neondb/auth",
    )
    tokens = list(
        stream_answer_tokens(
            settings,
            system_template="unused {sources}",
            sources=[],
            history=[],
            question="What is the capital?",
        )
    )
    assert tokens
    assert "couldn't find enough information" in "".join(tokens).lower()
