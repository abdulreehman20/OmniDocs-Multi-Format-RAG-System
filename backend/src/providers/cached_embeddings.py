from __future__ import annotations

from src.config import Settings
from src.providers.cache_keys import embedding_cache_key
from src.providers.protocols import Cache, EmbeddingProvider


class CachedEmbeddings:
    """Fail-open embedding cache wrapper around any EmbeddingProvider."""

    def __init__(
        self,
        inner: EmbeddingProvider,
        cache: Cache,
        settings: Settings,
    ) -> None:
        self._inner = inner
        self._cache = cache
        self._settings = settings

    @property
    def model_id(self) -> str:
        return self._inner.model_id

    @property
    def dimension(self) -> int:
        return self._inner.dimension

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        results: list[list[float] | None] = [None] * len(texts)
        missing_idx: list[int] = []
        missing_texts: list[str] = []
        for i, text in enumerate(texts):
            key = embedding_cache_key(
                model_id=self.model_id,
                preprocess_version=self._settings.embedding_preprocess_version,
                text=text,
            )
            hit = self._cache.get_json(key)
            if isinstance(hit, list) and hit:
                results[i] = [float(x) for x in hit]
            else:
                missing_idx.append(i)
                missing_texts.append(text)
        if missing_texts:
            fresh = self._inner.embed_documents(missing_texts)
            for j, vec in enumerate(fresh):
                i = missing_idx[j]
                results[i] = vec
                key = embedding_cache_key(
                    model_id=self.model_id,
                    preprocess_version=self._settings.embedding_preprocess_version,
                    text=missing_texts[j],
                )
                self._cache.set_json(
                    key,
                    vec,
                    ttl_seconds=self._settings.embedding_cache_ttl_seconds,
                )
        return [r or [] for r in results]

    def embed_query(self, text: str) -> list[float]:
        key = embedding_cache_key(
            model_id=self.model_id,
            preprocess_version=self._settings.embedding_preprocess_version,
            text=text,
        )
        hit = self._cache.get_json(key)
        if isinstance(hit, list) and hit:
            return [float(x) for x in hit]
        vec = self._inner.embed_query(text)
        self._cache.set_json(
            key,
            vec,
            ttl_seconds=self._settings.embedding_cache_ttl_seconds,
        )
        return vec
