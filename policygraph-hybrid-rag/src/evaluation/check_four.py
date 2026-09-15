from src.evaluation.eval_harness import (
    load_all_chunks,
    build_bm25,
    load_reranker,
)
from src.retrieval.dense import dense_search
from src.retrieval.bm25 import search_bm25
from src.retrieval.fusion import reciprocal_rank_fusion
from src.retrieval.reranker import rerank


DENSE_TOP_K = 20
BM25_TOP_K = 20
RRF_TOP_K = 10
RRF_K = 60
RERANK_TOP_K = 5


QUESTIONS = {
    "Q1": "What events are covered under Section I of the policy?",
    "Q12": "Is theft covered under the policy?",
    "Q13": "Is accidental external damage covered?",
}


def get_chunk(item):
    if isinstance(item, tuple):
        return item[0]

    if isinstance(item, dict) and "chunk" in item:
        return item["chunk"]

    return item


def find_rank(results, target_chunk_id):
    for rank, item in enumerate(results, start=1):
        chunk = get_chunk(item)

        if chunk.get("chunk_id") == target_chunk_id:
            return rank

    return None


chunks = load_all_chunks()
bm25 = build_bm25(chunks)
reranker = load_reranker()

target_chunk = chunks[1]
target_chunk_id = target_chunk["chunk_id"]

print("\nTarget chunk:")
print(target_chunk_id)
print(target_chunk["content"][:500])


for question_id, question in QUESTIONS.items():

    print("\n" + "=" * 90)
    print(question_id, "|", question)
    print("=" * 90)

    dense_results = dense_search(
        query=question,
        top_k=DENSE_TOP_K,
    )

    bm25_results = search_bm25(
        bm25=bm25,
        chunks=chunks,
        query=question,
        top_k=BM25_TOP_K,
    )

    rrf_results = reciprocal_rank_fusion(
        dense_results=dense_results,
        bm25_results=bm25_results,
        k=RRF_K,
        top_k=RRF_TOP_K,
    )

    rrf_chunks = [
        result["chunk"]
        for result in rrf_results
    ]

    reranked_results = rerank(
        reranker=reranker,
        query=question,
        chunks=rrf_chunks,
        top_k=RERANK_TOP_K,
    )

    print("\nTARGET CHUNK RANKS")

    print(
        "Dense:",
        find_rank(dense_results, target_chunk_id),
    )

    print(
        "BM25:",
        find_rank(bm25_results, target_chunk_id),
    )

    print(
        "RRF:",
        find_rank(rrf_results, target_chunk_id),
    )

    print(
        "Reranker:",
        find_rank(reranked_results, target_chunk_id),
    )

    print("\nRRF RESULTS")

    for rank, result in enumerate(
        rrf_results,
        start=1,
    ):
        chunk = result["chunk"]

        print(
            rank,
            "| RRF",
            round(result["score"], 5),
            "| page",
            chunk.get("page_number"),
            "|",
            chunk.get("section_number"),
            "|",
            chunk.get("chunk_id"),
        )

    print("\nRERANKED RESULTS")

    for rank, (chunk, score) in enumerate(
        reranked_results,
        start=1,
    ):
        print(
            rank,
            "| score",
            round(score, 4),
            "| page",
            chunk.get("page_number"),
            "|",
            chunk.get("section_number"),
            "|",
            chunk.get("chunk_id"),
        )