from __future__ import annotations

from typing import Any

from src.retrieval.bm25 import build_bm25, search_bm25
from src.retrieval.dense import dense_search
from src.retrieval.fusion import reciprocal_rank_fusion
from src.retrieval.reranker import load_reranker, rerank


# ============================================================
# Configuration
# ============================================================

DENSE_TOP_K = 20
BM25_TOP_K = 20
RRF_TOP_K = 20
RRF_K = 60
RERANK_TOP_K = 5


# ============================================================
# Helpers
# ============================================================

def _safe_results(
    results: list[tuple[dict[str, Any], float]],
) -> list[tuple[dict[str, Any], float]]:
    """Remove chunks flagged as prompt injection."""

    return [
        (chunk, score)
        for chunk, score in results
        if not chunk.get("prompt_injection", False)
    ]


def _build_bm25(chunks: list[dict[str, Any]]):
    """Build a BM25 index for the supplied corpus."""

    return build_bm25(chunks)


# ============================================================
# Dense Only
# ============================================================

def retrieve_dense_only(
    query: str,
) -> list[tuple[dict[str, Any], float]]:
    """
    Dense retrieval only.

    Pipeline:
        Query -> Dense Search -> Top K
    """

    results = dense_search(
        query=query,
        top_k=DENSE_TOP_K,
        include_prompt_injection=False,
    )

    return _safe_results(results)


# ============================================================
# Dense + BM25
# ============================================================

def retrieve_hybrid(
    query: str,
    chunks: list[dict[str, Any]],
    bm25=None,
) -> list[tuple[dict[str, Any], float]]:
    """
    Hybrid retrieval using Dense + BM25 + RRF.

    Pipeline:
        Dense
          \
           -> RRF -> Top K
          /
        BM25
    """

    if bm25 is None:
        bm25 = _build_bm25(chunks)

    dense_results = dense_search(
        query=query,
        top_k=DENSE_TOP_K,
        include_prompt_injection=False,
    )

    bm25_results = search_bm25(
        bm25=bm25,
        chunks=chunks,
        query=query,
        top_k=BM25_TOP_K,
    )

    fused_results = reciprocal_rank_fusion(
        dense_results=dense_results,
        bm25_results=bm25_results,
        k=RRF_K,
        top_k=RRF_TOP_K,
    )

    results = [
        (
            result["chunk"],
            result["score"],
        )
        for result in fused_results
    ]

    return _safe_results(results)


# ============================================================
# Hybrid + Reranking
# ============================================================

def retrieve_hybrid_reranked(
    query: str,
    chunks: list[dict[str, Any]],
    bm25=None,
    reranker=None,
) -> list[tuple[dict[str, Any], float]]:
    """
    Full retrieval pipeline.

    Pipeline:
        Dense + BM25
              |
             RRF
              |
        Cross-Encoder
              |
           Top K
    """

    hybrid_results = retrieve_hybrid(
        query=query,
        chunks=chunks,
        bm25=bm25,
    )

    if not hybrid_results:
        return []

    candidate_chunks = [
        chunk
        for chunk, _ in hybrid_results
    ]

    if reranker is None:
        reranker = load_reranker()

    reranked_results = rerank(
        reranker=reranker,
        query=query,
        chunks=candidate_chunks,
        top_k=RERANK_TOP_K,
    )

    return _safe_results(reranked_results)


# ============================================================
# Unified Interface
# ============================================================

def retrieve(
    query: str,
    config: str,
    chunks: list[dict[str, Any]],
    bm25=None,
    reranker=None,
) -> list[tuple[dict[str, Any], float]]:
    """
    Run one of the Day 13 retrieval configurations.

    Supported configurations:

        dense_only
        hybrid
        hybrid_reranked
    """

    if config == "dense_only":
        return retrieve_dense_only(
            query=query,
        )

    if config == "hybrid":
        return retrieve_hybrid(
            query=query,
            chunks=chunks,
            bm25=bm25,
        )

    if config == "hybrid_reranked":
        return retrieve_hybrid_reranked(
            query=query,
            chunks=chunks,
            bm25=bm25,
            reranker=reranker,
        )

    raise ValueError(
        f"Unknown ablation configuration: {config}. "
        "Expected one of: "
        "dense_only, hybrid, hybrid_reranked"
    )


# ============================================================
# Configuration Metadata
# ============================================================

ABLATION_CONFIGS = {
    "dense_only": {
        "name": "Dense Only",
        "dense": True,
        "bm25": False,
        "rrf": False,
        "reranking": False,
    },
    "hybrid": {
        "name": "Dense + BM25 + RRF",
        "dense": True,
        "bm25": True,
        "rrf": True,
        "reranking": False,
    },
    "hybrid_reranked": {
        "name": "Dense + BM25 + RRF + Reranking",
        "dense": True,
        "bm25": True,
        "rrf": True,
        "reranking": True,
    },
}
def retrieve_with_stages(query, chunks, bm25=None, reranker=None):
    """Run the retrieval pipeline while exposing each intermediate stage."""

    if bm25 is None:
        bm25 = _build_bm25(chunks)

    # Stage 1: Dense retrieval
    dense_results = dense_search(
        query,
        top_k=DENSE_TOP_K,
        include_prompt_injection=False,
    )
    dense_results = _safe_results(dense_results)

    # Stage 2: BM25 retrieval
    bm25_results = search_bm25(
        bm25=bm25,
        chunks=chunks,
        query=query,
        top_k=BM25_TOP_K,
    )
    bm25_results = _safe_results(bm25_results)

    # Stage 3: RRF fusion
    fused_results = reciprocal_rank_fusion(
        dense_results,
        bm25_results,
        k=RRF_K,
    )

    rrf_results = [
        (result["chunk"], result["score"])
        for result in fused_results[:RRF_TOP_K]
    ]
    rrf_results = _safe_results(rrf_results)

    # Stage 4: Cross-encoder reranking
    if reranker is None:
        reranker = load_reranker()

    rrf_chunks = [chunk for chunk, _ in rrf_results]

    if rrf_chunks:
        reranked_results = rerank(
            reranker,
            query,
            rrf_chunks,
            top_k=RERANK_TOP_K,
        )
        reranked_results = _safe_results(reranked_results)
    else:
        reranked_results = []

    return {
        "dense": dense_results,
        "bm25": bm25_results,
        "rrf": rrf_results,
        "reranked": reranked_results,
    }