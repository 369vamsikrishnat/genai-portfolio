"""Retrieval ablation: BM25 vs dense vs RRF vs RRF+rerank, leave-one-out with weak labels.

Weak relevance: a result is relevant if it shares (product, issue) with the query complaint.
Validate this proxy by hand-checking ~100 query->top-5 judgments and say so in the README.
Recall@k is not reported: with large relevant sets it is meaningless, so Precision@k is used.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np

from ..metrics import hit_at_k, mrr, ndcg_at_k, percentiles, precision_at_k
from ..retrieve import HybridRetriever


def run_ablation(retriever: HybridRetriever, meta, n_queries: int = 300, k: int = 10, seed: int = 0,
                 modes: tuple[str, ...] = HybridRetriever.MODES) -> dict:
    keys = (meta["product"].astype(str) + "||" + meta["issue"].astype(str)).to_numpy()
    _, uniq = np.unique(keys, return_inverse=True)
    group_size = np.bincount(uniq)
    rng = np.random.default_rng(seed)
    qs = rng.choice(len(meta), size=min(n_queries, len(meta)), replace=False)
    out: dict = {"n_queries": len(qs), "k": k, "n_docs": len(meta), "modes": {}}
    for mode in modes:
        if mode == "rrf_rerank" and retriever.reranker is None:
            continue
        agg: dict[str, list[float]] = {"hit@1": [], "hit@5": [], "p@5": [], "mrr": [], "ndcg@10": []}
        lat = []
        for q in qs:
            t0 = time.perf_counter()
            hits = retriever.search(retriever.texts[q], k=k + 1, mode=mode, need_dense_score=False)
            lat.append((time.perf_counter() - t0) * 1000)
            ids = [h.idx for h in hits if h.idx != q][:k]
            rels = [bool(uniq[i] == uniq[q]) for i in ids]
            n_rel = int(group_size[uniq[q]]) - 1
            agg["hit@1"].append(hit_at_k(rels, 1))
            agg["hit@5"].append(hit_at_k(rels, 5))
            agg["p@5"].append(precision_at_k(rels, 5))
            agg["mrr"].append(mrr(rels))
            agg["ndcg@10"].append(ndcg_at_k(rels, 10, n_rel))
        out["modes"][mode] = {**{m: round(float(np.mean(v)), 4) for m, v in agg.items()},
                              "latency_ms": percentiles(lat)}
    return out


def to_markdown(res: dict, meta: dict) -> str:
    head = ["| mode | Hit@1 | Hit@5 | P@5 | MRR | nDCG@10 | p50 ms | p95 ms | p99 ms |",
            "|---|---|---|---|---|---|---|---|---|"]
    rows = [f"| {m} | {r['hit@1']:.3f} | {r['hit@5']:.3f} | {r['p@5']:.3f} | {r['mrr']:.3f} | "
            f"{r['ndcg@10']:.3f} | {r['latency_ms']['p50']} | {r['latency_ms']['p95']} | {r['latency_ms']['p99']} |"
            for m, r in res["modes"].items()]
    note = (f"\n{res['n_queries']} leave-one-out queries over {res['n_docs']} complaints. Embedder: "
            f"`{meta['embedder']}`, reranker: `{meta['reranker']}`. Relevance = same (product, issue) "
            "(weak label). Latency is end-to-end single-threaded, query embedding included.\n")
    if meta["embedder"] == "hashing" or meta["reranker"] == "lexical":
        note += "\n> WARNING: hashing embedder and/or lexical stand-in reranker. Not valid results.\n"
    return "\n".join(head + rows) + note


def save(res: dict, results_dir: Path, docs_dir: Path, meta: dict) -> None:
    results_dir.mkdir(parents=True, exist_ok=True)
    docs_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / "retrieval_ablation.json").write_text(json.dumps({**res, "meta": meta}, indent=2))
    (docs_dir / "ablation.md").write_text("# Retrieval ablation\n\n" + to_markdown(res, meta))
