import time
from langfuse import observe
from google import genai

from src.ingestion.chunker import section_aware_split

from src.retrieval.dense import dense_search

from src.retrieval.bm25 import (
    build_bm25,
    search_bm25
)

from src.retrieval.fusion import (
    reciprocal_rank_fusion
)

from src.retrieval.reranker import (
    load_reranker,
    rerank
)

from src.generation.generator import generate
from src.api.cost_tracker import CostTracker


@observe(name="policygraph-rag-pipeline")
def run_pipeline(query, tracker=None):

    timings = {}

    if tracker is None:
       tracker = CostTracker()

    # --------------------------------------------------
    # Load policy
    # --------------------------------------------------

    with open(
        "data/synthetic_policies/policy_1.txt",
        "r",
        encoding="utf-8"
    ) as file:
        text = file.read()

    chunks = section_aware_split(
        text,
        "policy_1.txt"
    )

    # --------------------------------------------------
    # Build BM25
    # --------------------------------------------------

    start = time.perf_counter()

    bm25 = build_bm25(chunks)

    timings["bm25_build"] = (
        time.perf_counter() - start
    )

    # --------------------------------------------------
    # Load reranker
    # --------------------------------------------------

    start = time.perf_counter()

    reranker = load_reranker()

    timings["reranker_load"] = (
        time.perf_counter() - start
    )

    # --------------------------------------------------
    # Load Gemini
    # --------------------------------------------------

    client = genai.Client()

    # --------------------------------------------------
    # 1. Dense retrieval
    # --------------------------------------------------

    start = time.perf_counter()

    dense_results = dense_search(
        query,
        chunks,
        top_k=20
    )

    timings["dense"] = (
        time.perf_counter() - start
    )

    # --------------------------------------------------
    # 2. BM25 retrieval
    # --------------------------------------------------

    start = time.perf_counter()

    bm25_results = search_bm25(
        bm25,
        chunks,
        query,
        top_k=20
    )

    timings["bm25"] = (
        time.perf_counter() - start
    )

    # --------------------------------------------------
    # 3. RRF fusion
    # --------------------------------------------------

    start = time.perf_counter()

    rrf_results = reciprocal_rank_fusion(
        dense_results,
        bm25_results,
        k=60,
        top_k=20
    )

    timings["rrf"] = (
        time.perf_counter() - start
    )

    # --------------------------------------------------
    # Convert RRF results to chunks
    # --------------------------------------------------

    candidate_chunks = [
        result["chunk"]
        for result in rrf_results
    ]

    # --------------------------------------------------
    # 4. Cross-Encoder reranking
    # --------------------------------------------------

    start = time.perf_counter()

    reranked_results = rerank(
        reranker,
        query,
        candidate_chunks,
        top_k=5
    )

    timings["rerank"] = (
        time.perf_counter() - start
    )

    # --------------------------------------------------
    # 5. Generate grounded answer
    # --------------------------------------------------

    documents = [
        chunk["content"]
        for chunk, _ in reranked_results
    ]

    start = time.perf_counter()

    answer, usage_metadata = generate(
        question=query,
        documents=documents,
        client=client
    )

    timings["generate"] = (
        time.perf_counter() - start
    )

    # --------------------------------------------------
    # Record Gemini usage
    # --------------------------------------------------

    tracker.record(
    input_tokens=usage_metadata.prompt_token_count,
    output_tokens=usage_metadata.candidates_token_count,
    thinking_tokens=usage_metadata.thoughts_token_count


    )

    return (
        answer,
        reranked_results,
        timings,
        usage_metadata,
        tracker
    )


# --------------------------------------------------
# Main
# --------------------------------------------------

if __name__ == "__main__":

    query = "What is the coverage for flood damage?"

    (
        answer,
        reranked_results,
        timings,
        usage_metadata,
        tracker
    ) = run_pipeline(query)

    print("\n" + "=" * 80)
    print("QUERY")
    print("=" * 80)

    print(query)

    print("\n" + "=" * 80)
    print("GENERATED ANSWER")
    print("=" * 80)

    print(answer)

    print("\n" + "=" * 80)
    print("FINAL RERANKED RESULTS")
    print("=" * 80)

    for rank, (chunk, score) in enumerate(
        reranked_results,
        start=1
    ):
        print(
            f"\n{rank}. Cross-Encoder Score: "
            f"{score:.4f}"
        )

        print(chunk["content"])

    print("\n" + "=" * 80)
    print("TIMINGS")
    print("=" * 80)

    for step, duration in timings.items():
        print(
            f"{step:<20} {duration:.4f} seconds"
        )

    print("\n" + "=" * 80)
    print("COST TRACKING")
    print("=" * 80)

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