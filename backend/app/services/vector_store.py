from functools import lru_cache

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import settings

COLLECTION_NAME = "kb_chunks"


@lru_cache(maxsize=1)
def get_chroma_client():
    return chromadb.PersistentClient(
        path=settings.chroma_persist_dir,
        settings=ChromaSettings(anonymized_telemetry=False),
    )


def get_collection():
    client = get_chroma_client()
    return client.get_or_create_collection(name=COLLECTION_NAME, metadata={"hnsw:space": "cosine"})


def add_chunks(
    ids: list[str],
    embeddings: list[list[float]],
    documents: list[str],
    metadatas: list[dict],
) -> None:
    col = get_collection()
    col.add(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)


def delete_by_ids(vector_ids: list[str]) -> None:
    if not vector_ids:
        return
    col = get_collection()
    col.delete(ids=vector_ids)


def query_vectors(
    query_embedding: list[float],
    tenant_id: int,
    kb_ids: list[int],
    top_k: int,
) -> dict:
    col = get_collection()
    where = {
        "$and": [
            {"tenant_id": {"$eq": tenant_id}},
            {"kb_id": {"$in": kb_ids}},
        ]
    }
    return col.query(query_embeddings=[query_embedding], n_results=top_k, where=where, include=["documents", "metadatas", "distances"])
