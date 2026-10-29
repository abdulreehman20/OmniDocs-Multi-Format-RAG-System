from functools import lru_cache

from src.config import Settings, get_settings
from src.db.redis import cache_from_settings
from src.db.s3_storage import Boto3ObjectStorage
from src.providers.cached_embeddings import CachedEmbeddings
from src.providers.embeddings import OpenRouterEmbeddingsProvider
from src.providers.fakes import FakeEmbeddingProvider, FakeObjectStorage, FakeVectorStore
from src.providers.protocols import Cache, EmbeddingProvider, ObjectStorage, VectorStore
from src.providers.vector_store import PineconeVectorStore


@lru_cache
def get_object_storage() -> ObjectStorage:
    settings = get_settings()
    if settings.environment == "test":
        return FakeObjectStorage()
    return Boto3ObjectStorage(settings)


@lru_cache
def get_embedding_provider() -> EmbeddingProvider:
    settings = get_settings()
    cache = cache_from_settings(settings)
    if settings.environment == "test":
        inner: EmbeddingProvider = FakeEmbeddingProvider(
            model_id=settings.embedding_model_id,
            dimension=min(8, settings.embedding_dimension),
        )
    else:
        inner = OpenRouterEmbeddingsProvider(settings)
    return CachedEmbeddings(inner, cache, settings)


@lru_cache
def get_vector_store() -> VectorStore:
    settings = get_settings()
    if settings.environment == "test":
        return FakeVectorStore()
    return PineconeVectorStore(settings)


@lru_cache
def get_app_cache() -> Cache:
    return cache_from_settings(get_settings())


def clear_provider_caches() -> None:
    get_object_storage.cache_clear()
    get_embedding_provider.cache_clear()
    get_vector_store.cache_clear()
    get_app_cache.cache_clear()


def providers_from_settings(
    settings: Settings,
) -> tuple[ObjectStorage, EmbeddingProvider, VectorStore]:
    cache = cache_from_settings(settings)
    if settings.environment == "test":
        emb: EmbeddingProvider = FakeEmbeddingProvider(
            model_id=settings.embedding_model_id, dimension=8
        )
        return (
            FakeObjectStorage(),
            CachedEmbeddings(emb, cache, settings),
            FakeVectorStore(),
        )
    return (
        Boto3ObjectStorage(settings),
        CachedEmbeddings(OpenRouterEmbeddingsProvider(settings), cache, settings),
        PineconeVectorStore(settings),
    )
