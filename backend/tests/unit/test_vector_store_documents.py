import pytest

from src.providers.vector_store import _to_document


def test_to_document_flattens_metadata_onto_dense_field() -> None:
    doc = _to_document(
        {
            "id": "vec-1",
            "values": [0.1, 0.2],
            "metadata": {
                "document_id": "d1",
                "owner_id": "u1",
                "generation": 2,
                "chunk_index": 0,
                "text_sha256": "abc",
            },
        },
        dense_field="embeddings",
    )
    assert doc == {
        "_id": "vec-1",
        "embeddings": [0.1, 0.2],
        "document_id": "d1",
        "owner_id": "u1",
        "generation": 2,
        "chunk_index": 0,
        "text_sha256": "abc",
    }


def test_to_document_rejects_metadata_key_colliding_with_dense_field() -> None:
    with pytest.raises(ValueError, match="dense field"):
        _to_document(
            {
                "id": "vec-1",
                "values": [0.1],
                "metadata": {"embeddings": "nope"},
            },
            dense_field="embeddings",
        )
