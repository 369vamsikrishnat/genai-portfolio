import re

from rank_bm25 import BM25Okapi


# --------------------------------------------------
# Tokenization
# --------------------------------------------------

def tokenize(text: str) -> list[str]:
    """
    Tokenize policy text for BM25 retrieval.

    Preserves:
    - Normal words
    - Section references like 4(b)
    - Numbers
    """

    if not text:
        return []

    return re.findall(
        r"\b[\w]+(?:\([a-zA-Z0-9]+\))?\b",
        text.lower()
    )


# --------------------------------------------------
# Build BM25 index
# --------------------------------------------------

def build_bm25(chunks: list[dict]) -> BM25Okapi:
    """
    Build a BM25 index from document chunks.
    """

    if not chunks:
        raise ValueError(
            "Cannot build BM25 index from empty chunks."
        )

    tokenized_chunks = [
        tokenize(chunk.get("content", ""))
        for chunk in chunks
    ]

    return BM25Okapi(tokenized_chunks)


# --------------------------------------------------
# BM25 search
# --------------------------------------------------

def search_bm25(
    bm25: BM25Okapi,
    chunks: list[dict],
    query: str,
    top_k: int = 5
) -> list[tuple[dict, float]]:
    """
    Search chunks using BM25.

    Returns:
        List of (chunk, score) tuples
        ordered by descending relevance.
    """

    if not query or not query.strip():
        return []

    if not chunks:
        return []

    if top_k <= 0:
        raise ValueError(
            "top_k must be greater than 0."
        )

    tokenized_query = tokenize(query)

    if not tokenized_query:
        return []

    scores = bm25.get_scores(
        tokenized_query
    )

    ranked_results = sorted(
        zip(chunks, scores),
        key=lambda item: item[1],
        reverse=True
    )

    return [
        (
            chunk,
            float(score)
        )
        for chunk, score in ranked_results[:top_k]
    ]


# --------------------------------------------------
# Main - BM25 retrieval test
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

    from src.ingestion.chunker import (
        section_aware_split
    )

    chunks = section_aware_split(
        text,
        "policy_1.txt"
    )

    print(
        "Number of chunks:",
        len(chunks)
    )

    # --------------------------------------------------
    # Build BM25 index
    # --------------------------------------------------

    bm25 = build_bm25(
        chunks
    )

    # --------------------------------------------------
    # Test query
    # --------------------------------------------------

    query = (
        "What damage caused by flooding "
        "is covered?"
    )

    results = search_bm25(
        bm25=bm25,
        chunks=chunks,
        query=query,
        top_k=5
    )

    # --------------------------------------------------
    # Display results
    # --------------------------------------------------

    print(
        f"\n=== BM25 Results: {query} ==="
    )

    for rank, (
        chunk,
        score
    ) in enumerate(
        results,
        start=1
    ):

        print(
            f"\n{rank}. Score: {score:.4f}"
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
            f"Content:\n"
            f"{chunk.get('content')}"
        )


# --------------------------------------------------
# Run
# --------------------------------------------------

if __name__ == "__main__":
    main()