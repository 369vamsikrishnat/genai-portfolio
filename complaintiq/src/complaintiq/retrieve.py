"""BM25 + dense + Reciprocal Rank Fusion + reranker, with switchable modes for the ablation."""
from __future__ import annotations

import re
from dataclasses import dataclass

import numpy as np
from scipy import sparse
from sklearn.feature_extraction.text import CountVectorizer

from .quant import topk_indices


class BM25:
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b

    def fit(self, docs: list[str]) -> BM25:
        self.vec = CountVectorizer(lowercase=True, stop_words="english",
                                   token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z]+\b")
        tf = self.vec.fit_transform(docs).tocsr().astype(np.float32)
        n = tf.shape[0]
        df = np.bincount(tf.indices, minlength=tf.shape[1])
        idf = np.log(1 + (n - df + 0.5) / (df + 0.5)).astype(np.float32)
        dl = np.asarray(tf.sum(axis=1)).ravel()
        avg = max(float(dl.mean()), 1e-9)
        rows = np.repeat(np.arange(n), np.diff(tf.indptr))
        denom = tf.data + self.k1 * (1 - self.b + self.b * dl[rows] / avg)
        w = tf.data * (self.k1 + 1) / denom * idf[tf.indices]
        self.W = sparse.csr_matrix((w, tf.indices, tf.indptr), shape=tf.shape).tocsc()
        return self

    def scores(self, query: str) -> np.ndarray:
        q = self.vec.transform([query])
        if q.nnz == 0:
            return np.zeros(self.W.shape[0], dtype=np.float32)
        return np.asarray(self.W[:, q.indices].sum(axis=1)).ravel()

    def search(self, query: str, k: int) -> list[int]:
        return topk_indices(self.scores(query), k).tolist()


def rrf(rankings: list[list[int]], k: int = 60) -> list[tuple[int, float]]:
    fused: dict[int, float] = {}
    for ranking in rankings:
        for rank, idx in enumerate(ranking):
            fused[idx] = fused.get(idx, 0.0) + 1.0 / (k + rank + 1)
    return sorted(fused.items(), key=lambda kv: -kv[1])


class LexicalReranker:
    """Token-Jaccard stand-in so tests/demos run offline. NOT a real reranker."""

    name = "lexical"

    def score(self, query: str, docs: list[str]) -> np.ndarray:
        tok = lambda s: set(re.findall(r"[a-z]{3,}", s.lower()))  # noqa: E731
        qt = tok(query)
        return np.array([len(qt & tok(d)) / max(len(qt | tok(d)), 1) for d in docs], dtype=np.float32)


class CrossEncoderReranker:
    def __init__(self, model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2", batch_size: int = 32):
        from sentence_transformers import CrossEncoder

        self.name, self.batch_size = model, batch_size
        self.model = CrossEncoder(model, max_length=512)

    def score(self, query: str, docs: list[str]) -> np.ndarray:
        pairs = [(query[:1500], d[:1500]) for d in docs]
        return np.asarray(self.model.predict(pairs, batch_size=self.batch_size), dtype=np.float32)


def get_reranker(name: str):
    if name in ("none", "", None):
        return None
    if name == "lexical":
        return LexicalReranker()
    return CrossEncoderReranker(name if "/" in name else "cross-encoder/ms-marco-MiniLM-L-6-v2")


@dataclass
class Hit:
    idx: int
    score: float
    dense_score: float


class HybridRetriever:
    MODES = ("bm25", "dense", "rrf", "rrf_rerank")

    def __init__(self, texts: list[str], vectors: np.ndarray, embedder, bm25: BM25 | None = None,
                 reranker=None):
        self.texts, self.vectors, self.embedder = texts, vectors, embedder
        self.bm25 = bm25 or BM25().fit(texts)
        self.reranker = reranker

    def search(self, query: str, k: int = 5, mode: str = "rrf_rerank", candidates: int = 50,
               qvec: np.ndarray | None = None, need_dense_score: bool = True) -> list[Hit]:
        if mode not in self.MODES:
            raise ValueError(f"mode must be one of {self.MODES}")
        if mode == "rrf_rerank" and self.reranker is None:
            raise ValueError("rrf_rerank needs a reranker")
        need_q = mode != "bm25" or need_dense_score
        if need_q and qvec is None:
            qvec = self.embedder.encode([query])[0]
        n = max(candidates, k)
        if mode == "bm25":
            sc = self.bm25.scores(query)
            ranked = [(int(i), float(sc[i])) for i in topk_indices(sc, k)]
        elif mode == "dense":
            sc = self.vectors @ qvec
            ranked = [(int(i), float(sc[i])) for i in topk_indices(sc, k)]
        else:
            dense = topk_indices(self.vectors @ qvec, n).tolist()
            fused = rrf([self.bm25.search(query, n), dense])[:n]
            if mode == "rrf":
                ranked = fused[:k]
            else:
                ids = [i for i, _ in fused]
                rs = self.reranker.score(query, [self.texts[i] for i in ids])
                order = np.argsort(-rs)[:k]
                ranked = [(ids[j], float(rs[j])) for j in order]
        return [Hit(i, s, float(self.vectors[i] @ qvec) if qvec is not None else float("nan"))
                for i, s in ranked]
