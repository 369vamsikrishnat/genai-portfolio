from sentence_transformers import CrossEncoder


MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"


def load_reranker():
    return CrossEncoder(MODEL_NAME)


def rerank(reranker, query, chunks, top_k=5):
    pairs = [
        (query, chunk["content"])
        for chunk in chunks
    ]

    scores = reranker.predict(pairs)

    ranked = sorted(
        zip(chunks, scores),
        key=lambda x: x[1],
        reverse=True
    )

    return ranked[:top_k]

if __name__ == "__main__":
    reranker = load_reranker()

    query = "What water damage is covered?"

    chunks = [
        {
            "content": "Water damage caused by a sudden and accidental burst of an internal pipe may be covered."
        },
        {
            "content": "Damage caused intentionally by the policyholder is not covered."
        },
        {
            "content": "Flooding caused by external water sources may be covered."
        }
    ]

    results = rerank(
        reranker,
        query,
        chunks,
        top_k=3
    )

    print("\nReranked results:")

    for rank, (chunk, score) in enumerate(
        results,
        start=1
    ):
        print(
            f"\n{rank}. Score: {score:.4f}"
        )
        print(chunk["content"])
