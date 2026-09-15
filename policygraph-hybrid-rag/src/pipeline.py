from __future__ import annotations

import os
import time
from functools import lru_cache
from typing import Any

from dotenv import load_dotenv
from google import genai
from langfuse import observe

from src.api.cost_tracker import CostTracker
from src.generation.generator import generate
from src.retrieval.bm25 import build_bm25, search_bm25
from src.retrieval.dense import dense_search, load_all_chunks
from src.retrieval.fusion import reciprocal_rank_fusion
from src.retrieval.reranker import load_reranker, rerank


load_dotenv()


# ============================================================
# Configuration
# ============================================================

DENSE_TOP_K = int(
    os.getenv("DENSE_TOP_K", "20")
)

BM25_TOP_K = int(
    os.getenv("BM25_TOP_K", "20")
)

RRF_TOP_K = int(
    os.getenv("RRF_TOP_K", "20")
)

RRF_K = int(
    os.getenv("RRF_K", "60")
)

RERANK_TOP_K = int(
    os.getenv("RERANK_TOP_K", "5")
)


def _validate_configuration() -> None:
    """
    Validate retrieval configuration at application startup.
    """

    configuration = {
        "DENSE_TOP_K": DENSE_TOP_K,
        "BM25_TOP_K": BM25_TOP_K,
        "RRF_TOP_K": RRF_TOP_K,
        "RRF_K": RRF_K,
        "RERANK_TOP_K": RERANK_TOP_K,
    }

    for name, value in configuration.items():

        if value <= 0:
            raise ValueError(
                f"{name} must be greater than 0. "
                f"Received: {value}"
            )


_validate_configuration()


# ============================================================
# BM25 Index
# ============================================================

@lru_cache(maxsize=1)
def load_bm25_index():
    """
    Build and cache the BM25 index for the current process.

    The PostgreSQL database is the source of truth.

    The BM25 index is intentionally kept in process memory
    because the current corpus is small and does not require
    a separate search infrastructure.

    Returns:
        (
            bm25_index,
            chunks
        )

    Raises:
        RuntimeError:
            If no indexed chunks exist.
    """

    chunks = load_all_chunks(
        include_prompt_injection=False
    )

    if not chunks:
        raise RuntimeError(
            "No document chunks found in PostgreSQL. "
            "Run ingestion before querying the pipeline."
        )

    bm25 = build_bm25(
        chunks
    )

    return bm25, chunks


def refresh_bm25_index() -> None:
    """
    Clear the cached BM25 index.

    This must be called after successful document ingestion
    so newly indexed chunks become searchable.
    """

    load_bm25_index.cache_clear()


# ============================================================
# Gemini Client
# ============================================================

@lru_cache(maxsize=1)
def get_gemini_client() -> genai.Client:
    """
    Create and cache the Gemini client.

    Reusing the client avoids unnecessary initialization
    for every request.
    """

    return genai.Client()


# ============================================================
# Helpers
# ============================================================

def _filter_unsafe_results(
    results: list[tuple[dict[str, Any], float]],
) -> list[tuple[dict[str, Any], float]]:
    """
    Remove chunks flagged as containing prompt-injection
    content.

    This is a defense-in-depth check.

    Retrieval modules already exclude flagged chunks where
    possible, but the pipeline enforces the security boundary
    again before generation.
    """

    safe_results = []

    for chunk, score in results:

        if chunk.get(
            "prompt_injection",
            False,
        ):
            continue

        safe_results.append(
            (
                chunk,
                score,
            )
        )

    return safe_results


def _empty_pipeline_result(
    timings: dict[str, float],
    tracker: CostTracker,
):
    """
    Return the standard result when no usable context
    is available.
    """

    return (
        "NOT_IN_DOCUMENTS",
        [],
        timings,
        None,
        tracker,
    )


# ============================================================
# Main RAG Pipeline
# ============================================================

@observe(
    name="policygraph-rag-pipeline"
)
def run_pipeline(
    query: str,
    tracker: CostTracker | None = None,
):
    """
    Execute the complete PolicyGraph Hybrid RAG pipeline.

    Architecture:

        User Query
             │
             ├───────────────┐
             ▼               ▼
        Dense Search      BM25 Search
             │               │
             └───────┬───────┘
                     ▼
                    RRF
                     │
                     ▼
              Cross-Encoder
                Reranking
                     │
                     ▼
             Security Filter
                     │
                     ▼
             Grounded Gemini
                     │
                     ▼
              Answer + Sources

    PostgreSQL is the source of truth for indexed chunks.

    BM25 is cached in memory and refreshed after ingestion.
    """

    # ========================================================
    # Validate query
    # ========================================================

    if not query or not query.strip():
        raise ValueError(
            "Query cannot be empty."
        )

    query = query.strip()

    if tracker is None:
        tracker = CostTracker()

    timings: dict[str, float] = {}

    # ========================================================
    # 1. Load BM25 index
    # ========================================================

    start = time.perf_counter()

    bm25, chunks = load_bm25_index()

    timings["bm25_index_load"] = (
        time.perf_counter() - start
    )

    # ========================================================
    # 2. Load reranker
    # ========================================================

    start = time.perf_counter()

    reranker = load_reranker()

    timings["reranker_load"] = (
        time.perf_counter() - start
    )

    # ========================================================
    # 3. Load Gemini client
    # ========================================================

    start = time.perf_counter()

    client = get_gemini_client()

    timings["gemini_client_load"] = (
        time.perf_counter() - start
    )

    # ========================================================
    # 4. Dense Retrieval
    # ========================================================

    start = time.perf_counter()

    dense_results = dense_search(
        query=query,
        top_k=DENSE_TOP_K,
        include_prompt_injection=False,
    )

    timings["dense"] = (
        time.perf_counter() - start
    )

    # ========================================================
    # 5. BM25 Retrieval
    # ========================================================

    start = time.perf_counter()

    bm25_results = search_bm25(
        bm25=bm25,
        chunks=chunks,
        query=query,
        top_k=BM25_TOP_K,
    )

    timings["bm25"] = (
        time.perf_counter() - start
    )

    # ========================================================
    # 6. Reciprocal Rank Fusion
    # ========================================================

    start = time.perf_counter()

    rrf_results = reciprocal_rank_fusion(
        dense_results=dense_results,
        bm25_results=bm25_results,
        k=RRF_K,
        top_k=RRF_TOP_K,
    )

    timings["rrf"] = (
        time.perf_counter() - start
    )

    # ========================================================
    # No fused candidates
    # ========================================================

    if not rrf_results:
        return _empty_pipeline_result(
            timings=timings,
            tracker=tracker,
        )

    # ========================================================
    # 7. Cross-Encoder Reranking
    # ========================================================

    candidate_chunks = [
        result["chunk"]
        for result in rrf_results
    ]

    start = time.perf_counter()

    reranked_results = rerank(
        reranker=reranker,
        query=query,
        chunks=candidate_chunks,
        top_k=RERANK_TOP_K,
    )

    timings["rerank"] = (
        time.perf_counter() - start
    )

    # ========================================================
    # 8. Security Filtering
    # ========================================================

    safe_results = _filter_unsafe_results(
        reranked_results
    )

    reranked_results = safe_results

    # ========================================================
    # No safe context
    # ========================================================

    if not reranked_results:
        return _empty_pipeline_result(
            timings=timings,
            tracker=tracker,
        )

    # ========================================================
    # 9. Grounded Generation
    # ========================================================

    documents = [
        chunk
        for chunk, _ in reranked_results
    ]

    start = time.perf_counter()

    answer, usage_metadata = generate(
        question=query,
        documents=documents,
        client=client,
    )

    timings["generate"] = (
        time.perf_counter() - start
    )

    # ========================================================
    # 10. Record Model Usage
    # ========================================================

    if usage_metadata is not None:

        input_tokens = getattr(
            usage_metadata,
            "prompt_token_count",
            0,
        ) or 0

        output_tokens = getattr(
            usage_metadata,
            "candidates_token_count",
            0,
        ) or 0

        thinking_tokens = getattr(
            usage_metadata,
            "thoughts_token_count",
            0,
        ) or 0

        tracker.record(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            thinking_tokens=thinking_tokens,
        )

    # ========================================================
    # Return
    # ========================================================

    return (
        answer,
        reranked_results,
        timings,
        usage_metadata,
        tracker,
    )


# ============================================================
# Local Test
# ============================================================

if __name__ == "__main__":

    test_query = (
       "What is the policyholder's annual income?"
    )

    (
        answer,
        reranked_results,
        timings,
        usage_metadata,
        tracker,
    ) = run_pipeline(
        test_query
    )

    print(
        "\n"
        + "=" * 80
    )

    print("QUERY")

    print(
        "=" * 80
    )

    print(test_query)

    print(
        "\n"
        + "=" * 80
    )

    print("GENERATED ANSWER")

    print(
        "=" * 80
    )

    print(answer)

    print(
        "\n"
        + "=" * 80
    )

    print("FINAL RERANKED RESULTS")

    print(
        "=" * 80
    )

    for rank, (
        chunk,
        score,
    ) in enumerate(
        reranked_results,
        start=1,
    ):

        print(
            f"\n{rank}. "
            f"Cross-Encoder Score: "
            f"{score:.4f}"
        )

        print(
            f"Chunk ID: "
            f"{chunk.get('chunk_id')}"
        )

        print(
            f"Document: "
            f"{chunk.get('doc_name')}"
        )

        print(
            f"Page: "
            f"{chunk.get('page_number')}"
        )

        print(
            f"Section: "
            f"{chunk.get('section_number')}"
        )

        print(
            f"Title: "
            f"{chunk.get('section_title')}"
        )

        print(
            f"Extraction: "
            f"{chunk.get('extraction_method')}"
        )

        print(
            f"Prompt Injection: "
            f"{chunk.get('prompt_injection')}"
        )

        print("\nContent:")

        print(
            chunk.get(
                "content",
                "",
            )
        )

    print(
        "\n"
        + "=" * 80
    )

    print("TIMINGS")

    print(
        "=" * 80
    )

    for step, duration in timings.items():

        print(
            f"{step:<25}"
            f"{duration:.4f} seconds"
        )

    print(
        "\n"
        + "=" * 80
    )

    print("COST TRACKING")

    print(
        "=" * 80
    )

    print(
        f"Input tokens:       "
        f"{tracker.total_input_tokens}"
    )

    print(
        f"Output tokens:      "
        f"{tracker.total_output_tokens}"
    )

    print(
        f"Total cost:         "
        f"${tracker.total_cost:.6f}"
    )

    print(
        f"Average cost/query: "
        f"${tracker.average_cost_per_query():.6f}"
    )