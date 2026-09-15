from __future__ import annotations

import hashlib
from typing import Any


# --------------------------------------------------
# Chunk identity
# --------------------------------------------------

def _get_chunk_id(chunk: dict[str, Any]) -> str:
    """
    Return a stable identity for a chunk.

    Preferred order:
        1. Database chunk ID
        2. Explicit chunk_id
        3. Deterministic fallback identity

    The fallback exists to keep the fusion layer usable
    while the ingestion/database layer is being upgraded.
    Production chunks should have a real database ID.
    """

    if chunk.get("id") is not None:
        return f"db:{chunk['id']}"

    if chunk.get("chunk_id"):
        return f"chunk:{chunk['chunk_id']}"

    # Temporary deterministic fallback.
    #
    # This is intentionally based on metadata + content
    # rather than content alone so identical text appearing
    # in different documents/pages does not automatically
    # collapse into one result.
    identity = "|".join(
        [
            str(chunk.get("doc_name", "")),
            str(chunk.get("document_name", "")),
            str(chunk.get("page_number", "")),
            str(chunk.get("section_number", "")),
            str(chunk.get("section_title", "")),
            str(chunk.get("content", "")),
        ]
    )

    return (
        "fallback:"
        + hashlib.sha256(
            identity.encode("utf-8")
        ).hexdigest()
    )


# --------------------------------------------------
# Reciprocal Rank Fusion
# --------------------------------------------------

def reciprocal_rank_fusion(
    dense_results: list[tuple[dict[str, Any], float]],
    bm25_results: list[tuple[dict[str, Any], float]],
    k: int = 60,
    top_k: int = 20,
) -> list[dict[str, Any]]:
    """
    Combine dense and BM25 rankings using
    Reciprocal Rank Fusion (RRF).

    RRF score:

        1 / (k + rank)

    A chunk appearing in both retrieval systems
    receives contributions from both rankings.

    Args:
        dense_results:
            Dense retrieval results ordered by relevance.

        bm25_results:
            BM25 retrieval results ordered by relevance.

        k:
            RRF ranking constant. 60 is the commonly
            used default.

        top_k:
            Maximum number of fused results to return.

    Returns:
        A list of dictionaries:

        [
            {
                "chunk": {...},
                "score": 0.0325
            }
        ]
    """

    if k <= 0:
        raise ValueError(
            "k must be greater than 0."
        )

    if top_k <= 0:
        raise ValueError(
            "top_k must be greater than 0."
        )

    scores: dict[str, float] = {}
    chunks: dict[str, dict[str, Any]] = {}

    # --------------------------------------------------
    # Dense rankings
    # --------------------------------------------------

    for rank, (chunk, _) in enumerate(
        dense_results,
        start=1
    ):

        chunk_id = _get_chunk_id(
            chunk
        )

        chunks[chunk_id] = chunk

        scores[chunk_id] = (
            scores.get(chunk_id, 0.0)
            + 1.0 / (k + rank)
        )

    # --------------------------------------------------
    # BM25 rankings
    # --------------------------------------------------

    for rank, (chunk, _) in enumerate(
        bm25_results,
        start=1
    ):

        chunk_id = _get_chunk_id(
            chunk
        )

        chunks[chunk_id] = chunk

        scores[chunk_id] = (
            scores.get(chunk_id, 0.0)
            + 1.0 / (k + rank)
        )

    # --------------------------------------------------
    # Sort by RRF score
    # --------------------------------------------------

    ranked_ids = sorted(
        scores,
        key=scores.get,
        reverse=True
    )

    return [
        {
            "chunk": chunks[chunk_id],
            "score": float(
                scores[chunk_id]
            ),
        }
        for chunk_id in ranked_ids[:top_k]
    ]


# --------------------------------------------------
# Utility
# --------------------------------------------------

def extract_fused_chunks(
    rrf_results: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """
    Extract chunks from RRF results.

    This keeps the RRF result structure separate from
    the chunk structure used by the reranker.
    """

    return [
        result["chunk"]
        for result in rrf_results
    ]