from __future__ import annotations

import os
import time
from functools import lru_cache

from dotenv import load_dotenv
from google import genai

from src.api.cost_tracker import CostTracker
from src.api.semantic_cache import SemanticCache
from src.generation.generator import generate
from src.retrieval.bm25 import build_bm25, search_bm25
from src.retrieval.dense import (
    dense_search,
    embed_text,
    load_all_chunks,
)
from src.retrieval.fusion import (
    extract_fused_chunks,
    reciprocal_rank_fusion,
)
from src.retrieval.reranker import load_reranker, rerank


load_dotenv()


DENSE_TOP_K = 20
BM25_TOP_K = 20
RRF_TOP_K = 20
RERANK_TOP_K = 5


@lru_cache(maxsize=1)
def get_chunks() -> list[dict]:
    return load_all_chunks()


@lru_cache(maxsize=1)
def get_bm25_index():
    chunks = get_chunks()
    return build_bm25(chunks)


@lru_cache(maxsize=1)
def get_reranker():
    return load_reranker()


@lru_cache(maxsize=1)
def get_gemini_client() -> genai.Client:
    return genai.Client()


@lru_cache(maxsize=1)
def get_semantic_cache() -> SemanticCache:
    return SemanticCache(
        redis_url=os.getenv(
            "REDIS_URL",
            "redis://localhost:6379",
        ),
        similarity_threshold=float(
            os.getenv(
                "CACHE_SIMILARITY_THRESHOLD",
                "0.95",
            )
        ),
        ttl_seconds=int(
            os.getenv(
                "CACHE_TTL_SECONDS",
                "86400",
            )
        ),
    )


def _extract_usage_tokens(
    usage_metadata,
) -> tuple[int, int, int]:
    """
    Extract input, output, and thinking token counts
    from Gemini usage metadata.
    """

    if usage_metadata is None:
        return 0, 0, 0

    input_tokens = int(
        getattr(
            usage_metadata,
            "prompt_token_count",
            0,
        )
        or 0
    )

    output_tokens = int(
        getattr(
            usage_metadata,
            "candidates_token_count",
            0,
        )
        or 0
    )

    thinking_tokens = int(
        getattr(
            usage_metadata,
            "thoughts_token_count",
            0,
        )
        or 0
    )

    return (
        input_tokens,
        output_tokens,
        thinking_tokens,
    )


def run_pipeline(
    query: str,
    tracker: CostTracker | None = None,
    use_cache: bool = True,
):
    if tracker is None:
        tracker = CostTracker()

    timings: dict[str, float] = {}

    # --------------------------------------------------
    # Query embedding
    # --------------------------------------------------

    start = time.perf_counter()

    query_embedding = embed_text(query)

    timings["embedding"] = (
        time.perf_counter() - start
    )

    # --------------------------------------------------
    # Semantic cache lookup
    # --------------------------------------------------

    cache = get_semantic_cache()

    if use_cache:

        start = time.perf_counter()

        cached_result = cache.get(
            query_embedding
        )

        timings["cache_lookup"] = (
            time.perf_counter() - start
        )

        if cached_result is not None:

            cached_metadata = (
                cached_result.get(
                    "metadata",
                    {}
                )
            )

            cached_reranked_results = (
                cached_metadata.get(
                    "reranked_results",
                    []
                )
            )

            timings["cache_hit"] = 1.0

            return (
                cached_result["answer"],
                cached_reranked_results,
                timings,
                None,
                tracker,
            )

        timings["cache_hit"] = 0.0

    else:
        timings["cache_hit"] = 0.0

    # --------------------------------------------------
    # Dense retrieval
    # --------------------------------------------------

    start = time.perf_counter()

    dense_results = dense_search(
        query=query,
        top_k=DENSE_TOP_K,
        include_prompt_injection=False,
        query_embedding=query_embedding,
    )

    timings["dense"] = (
        time.perf_counter() - start
    )

    # --------------------------------------------------
    # BM25 retrieval
    # --------------------------------------------------

    start = time.perf_counter()

    chunks = get_chunks()
    bm25_index = get_bm25_index()

    bm25_results = search_bm25(
        bm25=bm25_index,
        chunks=chunks,
        query=query,
        top_k=BM25_TOP_K,
    )

    timings["bm25"] = (
        time.perf_counter() - start
    )

    # --------------------------------------------------
    # Reciprocal Rank Fusion
    # --------------------------------------------------

    start = time.perf_counter()

    fused_results = reciprocal_rank_fusion(
        dense_results=dense_results,
        bm25_results=bm25_results,
        top_k=RRF_TOP_K,
    )

    timings["rrf"] = (
        time.perf_counter() - start
    )

    # --------------------------------------------------
    # Cross-encoder reranking
    # --------------------------------------------------

    start = time.perf_counter()

    reranker = get_reranker()

    fused_chunks = extract_fused_chunks(
        fused_results
    )

    reranked_results = rerank(
        reranker=reranker,
        query=query,
        chunks=fused_chunks,
        top_k=RERANK_TOP_K,
    )

    timings["rerank"] = (
        time.perf_counter() - start
    )

    # --------------------------------------------------
    # Gemini generation
    # --------------------------------------------------

    start = time.perf_counter()

    client = get_gemini_client()

    answer, usage_metadata = generate(
        question=query,
        documents=[
            chunk
            for chunk, _ in reranked_results
        ],
        client=client,
    )

    timings["generate"] = (
        time.perf_counter() - start
    )

    # --------------------------------------------------
    # Token usage
    # --------------------------------------------------

    (
        input_tokens,
        output_tokens,
        thinking_tokens,
    ) = _extract_usage_tokens(
        usage_metadata
    )

    # --------------------------------------------------
    # Cost tracking
    # --------------------------------------------------

    cost = tracker.record(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        thinking_tokens=thinking_tokens,
        query=query,
    )

    # --------------------------------------------------
    # Semantic cache storage
    # --------------------------------------------------

    if use_cache:

        cache.set(
            query=query,
            embedding=query_embedding,
            answer=answer,
            metadata={
                "reranked_results": reranked_results,
                "timings": timings,
            },
        )

    return (
        answer,
        reranked_results,
        timings,
        cost,
        tracker,
    )