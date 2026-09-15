from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

from sentence_transformers import CrossEncoder


MODEL_NAME = os.getenv(
    "RERANKER_MODEL",
    "cross-encoder/ms-marco-MiniLM-L-6-v2",
)

RERANK_BATCH_SIZE = int(
    os.getenv("RERANK_BATCH_SIZE", "32")
)


@lru_cache(maxsize=1)
def load_reranker() -> CrossEncoder:
    """
    Load the cross-encoder reranker once per process.

    The cached model prevents expensive model initialization
    on every API request.
    """
    return CrossEncoder(MODEL_NAME)


def rerank(
    reranker: CrossEncoder,
    query: str,
    chunks: list[dict[str, Any]],
    top_k: int = 5,
) -> list[tuple[dict[str, Any], float]]:
    """
    Rerank retrieved chunks using a cross-encoder.

    Returns:
        List of (chunk, score) tuples sorted by descending score.
    """

    if not query or not query.strip():
        return []

    if not chunks:
        return []

    if top_k <= 0:
        raise ValueError(
            "top_k must be greater than 0."
        )

    pairs = [
        (
            query,
            chunk.get("content", "")
        )
        for chunk in chunks
    ]

    scores = reranker.predict(
        pairs,
        batch_size=RERANK_BATCH_SIZE,
        show_progress_bar=False,
    )

    ranked = sorted(
        (
            (
                chunk,
                float(score)
            )
            for chunk, score in zip(
                chunks,
                scores
            )
        ),
        key=lambda item: item[1],
        reverse=True,
    )

    return ranked[:top_k]


if __name__ == "__main__":
    reranker = load_reranker()

    query = "What water damage is covered?"

    chunks = [
        {
            "content": (
                "Water damage caused by a sudden and accidental "
                "burst of an internal pipe may be covered."
            )
        },
        {
            "content": (
                "Damage caused intentionally by the policyholder "
                "is not covered."
            )
        },
        {
            "content": (
                "Flooding caused by external water sources "
                "may be covered."
            )
        },
    ]

    results = rerank(
        reranker,
        query,
        chunks,
        top_k=3,
    )

    print("\nReranked results:")

    for rank, (chunk, score) in enumerate(
        results,
        start=1,
    ):
        print(
            f"\n{rank}. Score: {score:.4f}"
        )
        print(
            chunk.get("content", "")
        )