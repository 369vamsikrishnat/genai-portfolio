"""Vector quantisation + exact/approximate top-k (pure numpy) for the memory-vs-recall study."""
from __future__ import annotations

import numpy as np

_POPCOUNT = np.array([bin(i).count("1") for i in range(256)], dtype=np.uint8)


def topk_indices(scores: np.ndarray, k: int) -> np.ndarray:
    k = min(k, len(scores))
    idx = np.argpartition(-scores, k - 1)[:k]
    return idx[np.argsort(-scores[idx])]


def memory_bytes(n: int, dim: int = 384) -> dict[str, int]:
    return {"float32": n * dim * 4, "int8": n * dim, "binary": n * ((dim + 7) // 8)}


def to_int8(x: np.ndarray, scale: float | None = None) -> tuple[np.ndarray, float]:
    scale = scale or float(np.abs(x).max()) / 127.0 or 1.0
    return np.clip(np.rint(x / scale), -127, 127).astype(np.int8), scale


def to_binary(x: np.ndarray) -> np.ndarray:
    return np.packbits(x > 0, axis=1)


def topk_float(db: np.ndarray, q: np.ndarray, k: int) -> np.ndarray:
    return topk_indices(db @ q, k)


def scores_int8(db8: np.ndarray, q: np.ndarray, scale: float, chunk: int = 100_000) -> np.ndarray:
    out = np.empty(len(db8), dtype=np.float32)
    for i in range(0, len(db8), chunk):
        out[i:i + chunk] = db8[i:i + chunk].astype(np.float32) @ q
    return out * scale


def topk_int8(db8: np.ndarray, q: np.ndarray, scale: float, k: int) -> np.ndarray:
    return topk_indices(scores_int8(db8, q, scale), k)


def hamming_dist(dbits: np.ndarray, qbits: np.ndarray) -> np.ndarray:
    return _POPCOUNT[np.bitwise_xor(dbits, qbits)].sum(axis=1, dtype=np.int32)


def topk_binary(dbits: np.ndarray, qbits: np.ndarray, k: int) -> np.ndarray:
    return topk_indices(-hamming_dist(dbits, qbits).astype(np.float32), k)


def topk_binary_rescore(dbits: np.ndarray, db_rescore: np.ndarray, qbits: np.ndarray,
                        q: np.ndarray, k: int, oversample: int = 10,
                        scale: float | None = None) -> np.ndarray:
    """Hamming shortlist (k*oversample) then rescore with int8/float vectors."""
    short = topk_binary(dbits, qbits, k * oversample)
    cand = db_rescore[short].astype(np.float32) @ q
    if scale:
        cand = cand * scale
    return short[np.argsort(-cand)[:k]]


def recall_at_k(exact: np.ndarray, approx: np.ndarray) -> float:
    return len(set(exact.tolist()) & set(approx.tolist())) / max(len(exact), 1)
