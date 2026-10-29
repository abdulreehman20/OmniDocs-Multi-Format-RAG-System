from src.config import Settings, get_settings
from src.db.s3_storage import Boto3ObjectStorage
from src.providers.embeddings import OpenRouterEmbeddingsProvider
from src.providers.fakes import FakeEmbeddingProvider, FakeObjectStorage, FakeVectorStore
from src.providers.protocols import EmbeddingProvider, ObjectStorage, VectorStore
from src.providers.vector_store import PineconeVectorStore

_object_storage: ObjectStorage | None = None
_object_storage_key: tuple | None = None
_embedding_provider: EmbeddingProvider | None = None
_embedding_key: tuple | None = None
_vector_store: VectorStore | None = None
_vector_store_key: tuple | None = None


def get_object_storage() -> ObjectStorage:
    global _object_storage, _object_storage_key
    settings = get_settings()
    if settings.environment == "test":
        return FakeObjectStorage()
    key = (
        settings.aws_access_key_id,
        settings.aws_secret_access_key,
        settings.aws_region,
        settings.aws_endpoint_url_s3,
        settings.s3_bucket_documents,
    )
    if _object_storage is None or _object_storage_key != key:
        _object_storage = Boto3ObjectStorage(settings)
        _object_storage_key = key
    return _object_storage


def get_embedding_provider() -> EmbeddingProvider:
    global _embedding_provider, _embedding_key
    settings = get_settings()
    if settings.environment == "test":
        return FakeEmbeddingProvider(
            model_id=settings.embedding_model_id,
            dimension=min(8, settings.embedding_dimension),
        )
    key = (
        settings.openrouter_api_key,
        settings.openrouter_base_url,
        settings.embedding_model_id,
        settings.embedding_dimension,
    )
    if _embedding_provider is None or _embedding_key != key:
        _embedding_provider = OpenRouterEmbeddingsProvider(settings)
        _embedding_key = key
    return _embedding_provider


def get_vector_store() -> VectorStore:
    global _vector_store, _vector_store_key
    settings = get_settings()
    if settings.environment == "test":
        return FakeVectorStore()
    key = (
        settings.pinecone_api_key,
        settings.pinecone_index_host,
        settings.pinecone_index_name,
        settings.pinecone_dense_field,
    )
    if _vector_store is None or _vector_store_key != key:
        _vector_store = PineconeVectorStore(settings)
        _vector_store_key = key
    return _vector_store


def clear_provider_caches() -> None:
    global _object_storage, _object_storage_key
    global _embedding_provider, _embedding_key
    global _vector_store, _vector_store_key
    _object_storage = None
    _object_storage_key = None
    _embedding_provider = None
    _embedding_key = None
    _vector_store = None
    _vector_store_key = None


def providers_from_settings(
    settings: Settings,
) -> tuple[ObjectStorage, EmbeddingProvider, VectorStore]:
    if settings.environment == "test":
        return (
            FakeObjectStorage(),
            FakeEmbeddingProvider(model_id=settings.embedding_model_id, dimension=8),
            FakeVectorStore(),
        )
    return (
        Boto3ObjectStorage(settings),
        OpenRouterEmbeddingsProvider(settings),
        PineconeVectorStore(settings),
    )
