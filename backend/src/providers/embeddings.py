from langchain_openai import OpenAIEmbeddings

from src.config import Settings


class OpenRouterEmbeddingsProvider:
    """OpenRouter embeddings via LangChain OpenAI-compatible client."""

    def __init__(self, settings: Settings) -> None:
        if not settings.openrouter_api_key:
            raise ValueError("OPENROUTER_API_KEY is required for embeddings")
        self._model_id = settings.embedding_model_id
        self._dimension = settings.embedding_dimension
        self._client = OpenAIEmbeddings(
            model=settings.embedding_model_id,
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
            dimensions=settings.embedding_dimension,
        )

    @property
    def model_id(self) -> str:
        return self._model_id

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return self._client.embed_documents(texts)

    def embed_query(self, text: str) -> list[float]:
        return self._client.embed_query(text)
