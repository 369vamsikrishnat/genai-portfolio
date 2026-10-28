"""Ranking metrics over boolean relevance lists (rank order), plus latency percentiles."""
from __future__ import annotations

import math

import numpy as np


def hit_at_k(rels: list[bool], k: int) -> float:
    return float(any(rels[:k]))


def precision_at_k(rels: list[bool], k: int) -> float:
    top = rels[:k]
    return sum(top) / max(len(top), 1)


def mrr(rels: list[bool]) -> float:
    for i, r in enumerate(rels):
        if r:
            return 1.0 / (i + 1)
    return 0.0


def ndcg_at_k(rels: list[bool], k: int, n_relevant: int) -> float:
    dcg = sum(1.0 / math.log2(i + 2) for i, r in enumerate(rels[:k]) if r)
    ideal = sum(1.0 / math.log2(i + 2) for i in range(min(k, n_relevant)))
    return dcg / ideal if ideal else 0.0


def percentiles(values_ms: list[float]) -> dict[str, float]:
    a = np.asarray(values_ms, dtype=float)
    return {f"p{p}": round(float(np.percentile(a, p)), 3) for p in (50, 95, 99)}
