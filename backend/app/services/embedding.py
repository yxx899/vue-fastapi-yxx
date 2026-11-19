import hashlib
from functools import lru_cache

import numpy as np

from app.config import settings

_model = None


@lru_cache(maxsize=1)
def _load_model():
    if settings.embedding_mock:
        return None
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(settings.bge_model_name)


def embed_texts(texts: list[str]) -> list[list[float]]:
    if settings.embedding_mock or not texts:
        return [_mock_embed(t) for t in texts]
    model = _load_model()
    vectors = model.encode(texts, normalize_embeddings=True)
    return [v.tolist() for v in vectors]


def embed_query(text: str) -> list[float]:
    return embed_texts([text])[0]


def _mock_embed(text: str) -> list[float]:
    h = hashlib.sha256(text.encode("utf-8")).digest()
    arr = np.frombuffer(h, dtype=np.uint8).astype(np.float32)
    arr = np.resize(arr, 384)
    arr = arr / (np.linalg.norm(arr) + 1e-9)
    return arr.tolist()
