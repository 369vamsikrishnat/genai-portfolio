import numpy as np

from complaintiq import quant
from complaintiq.evals.scale import run_size, synthetic_vectors
from complaintiq.metrics import hit_at_k, mrr, ndcg_at_k, percentiles, precision_at_k


def test_ranking_metrics():
    rels = [False, True, False, True]
    assert hit_at_k(rels, 1) == 0.0 and hit_at_k(rels, 2) == 1.0
    assert precision_at_k(rels, 4) == 0.5
    assert mrr(rels) == 0.5 and mrr([False]) == 0.0
    assert abs(ndcg_at_k([True, True], 2, 2) - 1.0) < 1e-9
    assert ndcg_at_k([False, False], 2, 2) == 0.0


def test_percentiles_keys():
    assert set(percentiles([1, 2, 3, 4])) == {"p50", "p95", "p99"}


def test_memory_table_matches_plan():
    m = quant.memory_bytes(3_800_000, 384)
    assert abs(m["float32"] / 1e9 - 5.84) < 0.05
    assert abs(m["int8"] / 1e9 - 1.46) < 0.05
    assert abs(m["binary"] / 1e9 - 0.18) < 0.02


def test_topk_exact():
    db = np.eye(5, dtype=np.float32)
    assert quant.topk_float(db, db[3], 1)[0] == 3


def test_quantised_recall_ordering():
    db = synthetic_vectors(4000, 384, clusters=50, seed=0)
    qs = synthetic_vectors(60, 384, clusters=50, seed=1)
    r = run_size(db, qs, k=10)
    assert r["float32"]["recall@k"] == 1.0
    assert r["int8"]["recall@k"] >= 0.9
    assert r["binary+int8_rescore"]["recall@k"] >= r["binary"]["recall@k"]
    assert r["memory_mb"]["int8"] < r["memory_mb"]["float32"] and r["memory_mb"]["binary"] < r["memory_mb"]["int8"]
