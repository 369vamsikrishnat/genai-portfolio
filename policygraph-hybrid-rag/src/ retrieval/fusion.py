from src.ingestion.chunker import section_aware_split
from src.retrieval.dense import dense_search
from src.retrieval.bm25 import build_bm25, search_bm25


def reciprocal_rank_fusion(
    dense_results,
    bm25_results,
    k=60,
    top_k=5
):
    """
    Combine dense and BM25 rankings using
    Reciprocal Rank Fusion (RRF).

    RRF score:
        1 / (k + rank)

    k=60 is the standard/default value.
    """

    scores = {}

    # Add dense retrieval rankings
    for rank, (chunk, _) in enumerate(dense_results, start=1):

        chunk_id = chunk["content"]

        scores.setdefault(
            chunk_id,
            {
                "chunk": chunk,
                "score": 0
            }
        )

        scores[chunk_id]["score"] += 1 / (k + rank)

    # Add BM25 retrieval rankings
    for rank, (chunk, _) in enumerate(bm25_results, start=1):

        chunk_id = chunk["content"]

        scores.setdefault(
            chunk_id,
            {
                "chunk": chunk,
                "score": 0
            }
        )

        scores[chunk_id]["score"] += 1 / (k + rank)

    # Sort by fused RRF score
    ranked = sorted(
        scores.values(),
        key=lambda x: x["score"],
        reverse=True
    )

    return ranked[:top_k]


def print_results(title, results):
    """Print retrieval results in a readable format."""

    print(f"\n=== {title} ===")

    for rank, result in enumerate(results, start=1):

        # RRF results are dictionaries
        if isinstance(result, dict):
            chunk = result["chunk"]
            score = result["score"]

        # Dense/BM25 results are tuples
        else:
            chunk, score = result

        print(f"\n{rank}. Score: {score:.4f}")
        print(chunk["content"])


def main():

    # ---------------------------------------------------------
    # Load policy document
    # ---------------------------------------------------------

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

    # ---------------------------------------------------------
    # Build BM25 index once
    # ---------------------------------------------------------

    bm25 = build_bm25(chunks)

    # ---------------------------------------------------------
    # Test queries
    # ---------------------------------------------------------

    queries = [
        "What is covered for flood damage?",
        "Clause 4(b)",
        "What happens if property damage is intentional?",
        "How long do I have to report property damage?",
        "What water damage is covered?"
    ]

    # ---------------------------------------------------------
    # Run Dense + BM25 + RRF
    # ---------------------------------------------------------

    for query in queries:

        print("\n")
        print("=" * 80)
        print(f"QUERY: {query}")
        print("=" * 80)

        # Dense retrieval
        dense_results = dense_search(
            query,
            chunks,
            top_k=5
        )

        # BM25 retrieval
        bm25_results = search_bm25(
            bm25,
            chunks,
            query,
            top_k=5
        )

        # RRF fusion
        fused_results = reciprocal_rank_fusion(
            dense_results,
            bm25_results,
            k=60,
            top_k=5
        )

        # Display results
        print_results(
            "DENSE RESULTS",
            dense_results
        )

        print_results(
            "BM25 RESULTS",
            bm25_results
        )

        print_results(
            "RRF FUSED RESULTS",
            fused_results
        )


if __name__ == "__main__":
    main()
