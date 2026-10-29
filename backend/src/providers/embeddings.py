from openai import OpenAI

from src.config import Settings


class OpenRouterEmbeddingsProvider:
    """OpenRouter embeddings via the OpenAI-compatible HTTP API.

    Nvidia models (e.g. ``nvidia/nemotron-3.5-embed-1b:free``) require string
    (or multimodal) inputs. LangChain's default path sends tiktoken token ids,
    which OpenRouter rejects with 400 Invalid input format — so we call the
    OpenAI SDK directly with raw strings.
    """

    def __init__(self, settings: Settings) -> None:
        if not settings.openrouter_api_key:
            raise ValueError("OPENROUTER_API_KEY is required for embeddings")
        self._model_id = settings.embedding_model_id
        self._dimension = settings.embedding_dimension
        self._client = OpenAI(
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
        )

    @property
    def model_id(self) -> str:
        return self._model_id

    @property
    def dimension(self) -> int:
        return self._dimension

    def _embed(self, texts: list[str]) -> list[list[float]]:
        # OpenRouter/Nvidia: input must be strings (not token-id arrays)
        response = self._client.embeddings.create(
            model=self._model_id,
            input=texts,
            dimensions=self._dimension,
        )
        by_index = sorted(response.data, key=lambda row: row.index)
        return [list(row.embedding) for row in by_index]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        cleaned = [t if isinstance(t, str) else str(t) for t in texts]
        # Batch to keep request size reasonable
        out: list[list[float]] = []
        batch_size = 32
        for i in range(0, len(cleaned), batch_size):
            out.extend(self._embed(cleaned[i : i + batch_size]))
        return out

    def embed_query(self, text: str) -> list[float]:
        return self._embed([text if isinstance(text, str) else str(text)])[0]
