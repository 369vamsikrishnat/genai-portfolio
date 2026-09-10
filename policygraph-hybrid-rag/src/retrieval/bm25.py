import re
from rank_bm25 import BM25Okapi


def tokenize(text):
    return re.findall(r"\b\w+(?:\(\w+\))?\b", text.lower())


def build_bm25(chunks):
    tokenized_chunks = [
        tokenize(chunk["content"])
        for chunk in chunks
    ]

    return BM25Okapi(tokenized_chunks)


def search_bm25(bm25, chunks, query, top_k=5):
    tokenized_query = tokenize(query)

    scores = bm25.get_scores(tokenized_query)

    ranked = sorted(
        zip(chunks, scores),
        key=lambda x: x[1],
        reverse=True
    )

    return ranked[:top_k]


if __name__ == "__main__":
    from src.ingestion.chunker import section_aware_split

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

    bm25 = build_bm25(chunks)

    query = "what is covered" #query = "Clause 4(b)"

    results = search_bm25(
        bm25,
        chunks,
        query,
        top_k=5
    )

    print("\n=== BM25: what is covered ===")

    for chunk, score in results:
        print(f"\n{score:.4f} | {chunk['content']}")
