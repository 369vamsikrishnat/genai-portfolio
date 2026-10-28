"""Embedders. `hashing` is an offline lexical stand-in for CI/demos; use a real model for results."""
from __future__ import annotations

import numpy as np
from sklearn.feature_extraction.text import HashingVectorizer
from sklearn.preprocessing import normalize

DEFAULT_DIM = 384
ALIASES = {"bge-small": "BAAI/bge-small-en-v1.5", "bge-base": "BAAI/bge-base-en-v1.5",
           "minilm": "sentence-transformers/all-MiniLM-L6-v2"}


class HashingEmbedder:
    """Signed hashed uni+bigram TF (sublinear), L2-normalised. Deterministic, no downloads."""

    def __init__(self, dim: int = DEFAULT_DIM):
        self.dim, self.name = dim, "hashing"
        self._vec = HashingVectorizer(n_features=dim, alternate_sign=True, norm=None,
                                      ngram_range=(1, 2), stop_words="english")

    def encode(self, texts: list[str], batch_size: int = 4096) -> np.ndarray:
        out = np.zeros((len(texts), self.dim), dtype=np.float32)
        for i in range(0, len(texts), batch_size):
            x = self._vec.transform(texts[i:i + batch_size])
            x.data = np.sign(x.data) * np.log1p(np.abs(x.data))
            out[i:i + batch_size] = normalize(x).toarray()
        return out


class SentenceTransformerEmbedder:
    def __init__(self, model: str, batch_size: int = 64):
        from sentence_transformers import SentenceTransformer  # needs `pip install .[embed]`

        self.name = ALIASES.get(model, model)
        self.model = SentenceTransformer(self.name)
        self.dim = self.model.get_sentence_embedding_dimension()
        self.batch_size = batch_size

    def encode(self, texts: list[str], batch_size: int | None = None) -> np.ndarray:
        v = self.model.encode(texts, batch_size=batch_size or self.batch_size,
                              normalize_embeddings=True, show_progress_bar=len(texts) > 2000)
        return np.asarray(v, dtype=np.float32)


def get_embedder(name: str = "hashing"):
    if name == "hashing":
        return HashingEmbedder()
    return SentenceTransformerEmbedder(name)
