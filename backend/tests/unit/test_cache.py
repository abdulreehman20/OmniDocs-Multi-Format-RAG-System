from src.config import Settings
from src.providers.cache import FakeCache
from src.providers.cache_keys import embedding_cache_key, retrieval_cache_key
from src.providers.cached_embeddings import CachedEmbeddings
from src.providers.fakes import FakeEmbeddingProvider


def _settings(**kwargs) -> Settings:
    base = dict(
        database_url="sqlite://",
        database_url_pooled="sqlite://",
        neon_auth_base_url="https://auth.example.neon.tech/neondb/auth",
        embedding_cache_ttl_seconds=60,
        embedding_preprocess_version="v1",
    )
    base.update(kwargs)
    return Settings(**base)


def test_embedding_cache_hit_and_isolation():
    cache = FakeCache()
    inner = FakeEmbeddingProvider(dimension=4)
    wrapped = CachedEmbeddings(inner, cache, _settings())
    v1 = wrapped.embed_query("hello")
    assert cache.store
    key = embedding_cache_key(
        model_id=inner.model_id, preprocess_version="v1", text="hello"
    )
    assert key in cache.store
    v2 = wrapped.embed_query("hello")
    assert v1 == v2


def test_cache_fail_open():
    cache = FakeCache()
    cache.fail_open = True
    inner = FakeEmbeddingProvider(dimension=4)
    wrapped = CachedEmbeddings(inner, cache, _settings())
    vec = wrapped.embed_query("hello")
    assert len(vec) == 4
    assert cache.store == {}


def test_retrieval_keys_differ_by_owner_and_corpus():
    k1 = retrieval_cache_key(
        owner_id="a",
        corpus_version=1,
        query="q",
        retrieval_version="baseline-v1",
        scope={"documents": [{"id": "d1", "generation": 1}]},
    )
    k2 = retrieval_cache_key(
        owner_id="b",
        corpus_version=1,
        query="q",
        retrieval_version="baseline-v1",
        scope={"documents": [{"id": "d1", "generation": 1}]},
    )
    k3 = retrieval_cache_key(
        owner_id="a",
        corpus_version=2,
        query="q",
        retrieval_version="baseline-v1",
        scope={"documents": [{"id": "d1", "generation": 1}]},
    )
    assert k1 != k2
    assert k1 != k3
