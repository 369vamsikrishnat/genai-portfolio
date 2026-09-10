from google import genai

from src.ingestion.chunker import section_aware_split

from src.retrieval.dense import dense_search

from src.retrieval.bm25 import (
    build_bm25,
    search_bm25
)

from src.retrieval.reranker import (
    load_reranker,
    rerank
)

from src.generation.generator import generate


# --------------------------------------------------
# Reciprocal Rank Fusion
# --------------------------------------------------

def reciprocal_rank_fusion(
    dense_results,
    bm25_results,
    k=60,
    top_k=20
):
    """
    Combine dense and BM25 rankings using
    Reciprocal Rank Fusion.

    RRF score:
        1 / (k + rank)
    """

    scores = {}

    # Dense rankings
    for rank, (chunk, _) in enumerate(
        dense_results,
        start=1
    ):

        chunk_id = chunk["content"]

        scores.setdefault(
            chunk_id,
            {
                "chunk": chunk,
                "score": 0
            }
        )

        scores[chunk_id]["score"] += (
            1 / (k + rank)
        )

    # BM25 rankings
    for rank, (chunk, _) in enumerate(
        bm25_results,
        start=1
    ):

        chunk_id = chunk["content"]

        scores.setdefault(
            chunk_id,
            {
                "chunk": chunk,
                "score": 0
            }
        )

        scores[chunk_id]["score"] += (
            1 / (k + rank)
        )

    ranked = sorted(
        scores.values(),
        key=lambda x: x["score"],
        reverse=True
    )

    return ranked[:top_k]


# --------------------------------------------------
# Main
# --------------------------------------------------

def main():

    # --------------------------------------------------
    # Load policy
    # --------------------------------------------------

    with open(
        "data/synthetic_policies/policy_1.txt",
        "r",
        encoding="utf-8"
    ) as file:

        text = file.read()

    # --------------------------------------------------
    # Create chunks
    # --------------------------------------------------

    chunks = section_aware_split(
        text,
        "policy_1.txt"
    )

    print(
        f"Loaded {len(chunks)} chunks."
    )

    # --------------------------------------------------
    # Build BM25 index
    # --------------------------------------------------

    bm25 = build_bm25(chunks)

    # --------------------------------------------------
    # Load cross-encoder reranker
    # --------------------------------------------------

    reranker = load_reranker()

    # --------------------------------------------------
    # Load Gemini client
    # --------------------------------------------------

    client = genai.Client()

    # --------------------------------------------------
    # Test queries
    # --------------------------------------------------

    queries = [
    "What happens if property damage is intentional?"
]

    # --------------------------------------------------
    # Retrieval pipeline
    # --------------------------------------------------

    for query in queries:

        print("\n")
        print("=" * 80)
        print(f"QUERY: {query}")
        print("=" * 80)

        # --------------------------------------------------
        # 1. Dense retrieval
        # --------------------------------------------------

        dense_results = dense_search(
            query,
            chunks,
            top_k=20
        )

        # --------------------------------------------------
        # 2. BM25 retrieval
        # --------------------------------------------------

        bm25_results = search_bm25(
            bm25,
            chunks,
            query,
            top_k=20
        )

        # --------------------------------------------------
        # 3. RRF fusion
        # --------------------------------------------------

        rrf_results = reciprocal_rank_fusion(
            dense_results,
            bm25_results,
            k=60,
            top_k=20
        )

        # --------------------------------------------------
        # Convert RRF results into chunks
        # --------------------------------------------------

        candidate_chunks = [
            result["chunk"]
            for result in rrf_results
        ]

        # --------------------------------------------------
        # 4. Cross-encoder reranking
        # --------------------------------------------------

        reranked_results = rerank(
            reranker,
            query,
            candidate_chunks,
            top_k=5
        )

        # --------------------------------------------------
        # 5. Generate grounded answer
        # --------------------------------------------------

        documents = [
            chunk["content"]
            for chunk, _ in reranked_results
        ]

        answer = generate(
            question=query,
            documents=documents,
            client=client
        )

        print("\n=== GENERATED ANSWER ===")
        print(answer)

        # --------------------------------------------------
        # 6. Final reranked results
        # --------------------------------------------------

        print("\n=== FINAL RERANKED RESULTS ===")

        for rank, (chunk, score) in enumerate(
            reranked_results,
            start=1
        ):

            print(
                f"\n{rank}. Cross-Encoder Score: "
                f"{score:.4f}"
            )

            print(
                chunk["content"]
            )


if __name__ == "__main__":
    main()