import pytest

from complaintiq.embed import HashingEmbedder
from complaintiq.evals.retrieval import run_ablation
from complaintiq.retrieve import BM25, HybridRetriever, LexicalReranker, rrf

DOCS = ["unauthorized charge on my credit card", "foreclosure notice from mortgage servicer",
        "debt collector keeps calling my phone", "overdraft fee charged on my checking account",
        "credit report shows an account that is not mine"]


def test_bm25_finds_relevant_doc():
    bm = BM25().fit(DOCS)
    assert bm.search("mortgage foreclosure", 1) == [1]
    assert bm.search("zzzz qqqq", 3) is not None  # unseen terms must not crash


def test_rrf_prefers_consensus():
    fused = rrf([[1, 2, 3], [2, 1, 4]])
    assert {fused[0][0], fused[1][0]} == {1, 2}


@pytest.fixture()
def retriever():
    emb = HashingEmbedder()
    return HybridRetriever(DOCS, emb.encode(DOCS), emb, reranker=LexicalReranker())


@pytest.mark.parametrize("mode", HybridRetriever.MODES)
def test_all_modes_return_top_hit(retriever, mode):
    hits = retriever.search("unauthorized charge on credit card", k=2, mode=mode)
    assert hits[0].idx == 0 and len(hits) == 2


def test_mode_validation(retriever):
    with pytest.raises(ValueError):
        retriever.search("x", mode="nope")
    retriever.reranker = None
    with pytest.raises(ValueError):
        retriever.search("x", mode="rrf_rerank")


def test_ablation_runs_and_beats_chance(synth_df):
    df = synth_df[synth_df.narrative.fillna("").str.len() > 0].reset_index(drop=True).head(1500)
    texts = df.narrative.tolist()
    emb = HashingEmbedder()
    ret = HybridRetriever(texts, emb.encode(texts), emb, reranker=LexicalReranker())
    res = run_ablation(ret, df, n_queries=40, k=10)
    assert set(res["modes"]) == set(HybridRetriever.MODES)
    n_groups = df.groupby(["product", "issue"]).ngroups
    for m in res["modes"].values():
        assert m["hit@1"] > 1.0 / n_groups and m["latency_ms"]["p50"] > 0
