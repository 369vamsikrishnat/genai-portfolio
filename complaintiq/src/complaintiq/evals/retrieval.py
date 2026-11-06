"""Retrieval ablation: BM25 vs dense vs RRF vs RRF+rerank, leave-one-out with weak labels.

Weak relevance: a result is relevant if it shares (product, issue) with the query complaint.
Validate this proxy by hand-checking ~100 query->top-5 judgments and say so in the README.
Recall@k is not reported: with large relevant sets it is meaningless, so Precision@k is used.
"""
from __future__ import annotations

import json
import hashlib
import time
from pathlib import Path

import numpy as np

from ..metrics import hit_at_k, mrr, ndcg_at_k, percentiles, precision_at_k
from ..report import normalized_hash_series
from ..retrieve import BM25, HybridRetriever


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


def run_temporal_evaluation(art, n_queries: int = 500, seed: int = 0, reranker=None, modes: tuple[str, ...] = ("bm25", "dense", "rrf")) -> dict:
    """Evaluate held-out later complaints against a train-only, template-deduped index.

    Relevance is the existing weak proxy: same product and issue as the query complaint.
    """
    n_train = int(art.manifest["n_train"])
    if not 0 < n_train < len(art.meta):
        raise ValueError(f"invalid temporal split: n_train={n_train}, rows={len(art.meta)}")
    if len(art.vectors) != len(art.meta):
        raise ValueError("artifact vectors and metadata have different row counts")

    meta = art.meta.reset_index(drop=True)
    train = meta.iloc[:n_train]
    test = meta.iloc[n_train:]
    split_date = train["date_received"].max()
    later_mask = test["date_received"] > split_date
    test_positions = np.arange(n_train, len(meta))[later_mask.to_numpy()]
    test = meta.iloc[test_positions]

    train_hashes = normalized_hash_series(train["narrative"])
    train_unique_mask = ~train_hashes.duplicated(keep="first")
    train_positions = np.arange(n_train)[train_unique_mask.to_numpy()]
    train = meta.iloc[train_positions]
    train_hash_set = set(train_hashes[train_unique_mask])

    test_hashes = normalized_hash_series(test["narrative"])
    no_train_template_overlap = ~test_hashes.isin(train_hash_set)
    no_test_template_duplicate = ~test_hashes.duplicated(keep="first")
    query_mask = no_train_template_overlap & no_test_template_duplicate
    query_positions = test_positions[query_mask.to_numpy()]
    test = meta.iloc[query_positions]

    train_keys = (train["product"].astype(str) + "||" + train["issue"].astype(str)).to_numpy()
    test_keys = (test["product"].astype(str) + "||" + test["issue"].astype(str)).to_numpy()
    known_keys = set(train_keys)
    has_relevance = np.asarray([key in known_keys for key in test_keys])
    query_positions = query_positions[has_relevance]
    test = test.iloc[np.flatnonzero(has_relevance)]
    test_keys = test_keys[has_relevance]
    if not len(test):
        raise ValueError("no later, non-duplicate test queries have a matching train relevance group")

    rng = np.random.default_rng(seed)
    selected = rng.choice(len(test), size=min(n_queries, len(test)), replace=False)
    queries = test.iloc[selected]
    query_keys = test_keys[selected]
    query_texts = queries["narrative"].astype(str).tolist()

    train_texts = train["narrative"].astype(str).tolist()
    train_vectors = art.vectors[train_positions]
    t0 = time.perf_counter()
    train_bm25 = BM25().fit(train_texts)
    bm25_build_ms = round((time.perf_counter() - t0) * 1000, 3)
    retriever = HybridRetriever(train_texts, train_vectors, art.embedder, bm25=train_bm25, reranker=reranker)
    relevant_counts = {key: int(np.count_nonzero(train_keys == key)) for key in set(query_keys)}

    modes = tuple(modes)
    aggregate: dict[str, dict[str, list[float]]] = {
        mode: {
            "hit@1": [], "hit@5": [], "hit@10": [],
            "p@1": [], "p@5": [], "p@10": [],
            "mrr@10": [], "ndcg@5": [], "ndcg@10": [],
            "query_embedding_ms": [], "search_latency_ms": [], "end_to_end_latency_ms": [],
        }
        for mode in modes
    }

    def search_one(mode: str, query: str, vector: np.ndarray | None):
        if mode == "bm25":
            return retriever.search(query, k=10, mode=mode, need_dense_score=False)
        return retriever.search(query, k=10, mode=mode, qvec=vector, need_dense_score=False)

    for mode in modes:
        vector = None
        if mode != "bm25":
            vector = art.embedder.encode([query_texts[0]])[0]
        search_one(mode, query_texts[0], vector)

    for idx, (query, expected_key) in enumerate(zip(query_texts, query_keys, strict=True)):
        for mode in modes:
            query_ms = 0.0
            vector = None
            if mode != "bm25":
                t0 = time.perf_counter()
                vector = art.embedder.encode([query])[0]
                query_ms = (time.perf_counter() - t0) * 1000
            t0 = time.perf_counter()
            hits = search_one(mode, query, vector)
            search_ms = (time.perf_counter() - t0) * 1000
            retrieved_keys = [train_keys[hit.idx] for hit in hits]
            rels = [key == expected_key for key in retrieved_keys]
            values = aggregate[mode]
            for cutoff in (1, 5, 10):
                values[f"hit@{cutoff}"].append(hit_at_k(rels, cutoff))
                values[f"p@{cutoff}"].append(precision_at_k(rels, cutoff))
            values["mrr@10"].append(mrr(rels))
            values["ndcg@5"].append(ndcg_at_k(rels, 5, relevant_counts[expected_key]))
            values["ndcg@10"].append(ndcg_at_k(rels, 10, relevant_counts[expected_key]))
            values["query_embedding_ms"].append(query_ms)
            values["search_latency_ms"].append(search_ms)
            values["end_to_end_latency_ms"].append(query_ms + search_ms)

    mode_results = {}
    for mode, metrics in aggregate.items():
        mode_results[mode] = {
            **{
                key: round(float(np.mean(values)), 4)
                for key, values in metrics.items()
                if key not in {"query_embedding_ms", "search_latency_ms", "end_to_end_latency_ms"}
            },
            "query_embedding_latency_ms": percentiles(metrics["query_embedding_ms"]),
            "search_latency_ms": percentiles(metrics["search_latency_ms"]),
            "end_to_end_latency_ms": percentiles(metrics["end_to_end_latency_ms"]),
        }

    query_ids = queries["complaint_id"].astype(str).tolist()
    id_digest = hashlib.sha256("\n".join(query_ids).encode()).hexdigest()
    return {
        "evaluation_type": "temporal_holdout_with_weak_labels",
        "relevance": {
            "type": "proxy",
            "definition": "same product and issue as query complaint",
            "source": "dataset labels; not human relevance judgments",
            "limitations": (
                "Measures taxonomy similarity, not whether a result is useful precedent or semantically similar."
            ),
        },
        "embedder_note": (
            "The hashing embedder is a deterministic n-gram lexical stand-in, not a semantic embedding model."
        ),
        "split": {
            "strategy": "train artifact rows vs strictly later held-out rows",
            "train_rows": n_train,
            "train_index_rows": len(train),
            "duplicate_train_templates_removed": n_train - len(train),
            "artifact_test_rows": len(meta) - n_train,
            "test_rows_after_strict_date": int(later_mask.sum()),
            "same_boundary_date_excluded": int((~later_mask).sum()),
            "cross_split_template_queries_excluded": int((~no_train_template_overlap).sum()),
            "duplicate_test_template_queries_excluded": int(
                (no_train_template_overlap & ~no_test_template_duplicate).sum()
            ),
            "queries_without_train_relevance_group_excluded": int((~has_relevance).sum()),
            "train_max_date": str(split_date.date()),
            "test_min_date": str(test["date_received"].min().date()),
            "test_max_date": str(test["date_received"].max().date()),
            "duplicate_complaint_ids": int(meta["complaint_id"].duplicated().sum()),
            "cross_split_template_hashes_before_exclusion": int(
                len(set(normalized_hash_series(meta.iloc[:n_train]["narrative"]))
                    & set(normalized_hash_series(meta.iloc[n_train:]["narrative"])))
            ),
        },
        "n_queries_available": len(test),
        "n_queries": len(query_ids),
        "query_ids": query_ids,
        "query_ids_sha256": id_digest,
        "seed": seed,
        "k": 10,
        "retrieval_config": {"rrf_candidate_depth": 50, "rrf_constant": 60},
        "n_retrieval_docs": len(train),
        "index_build_ms": {"bm25": bm25_build_ms, "dense": 0.0},
        "latency_methodology": (
            "Single-query latency after one warm-up per mode. Search latency excludes query embedding; "
            "end-to-end latency includes query embedding for dense and RRF. BM25 does not embed queries."
        ),
        "n_relevant_by_query": {
            str(query_id): relevant_counts[key]
            for query_id, key in zip(query_ids, query_keys, strict=True)
        },
        "modes": mode_results,
    }


def temporal_to_markdown(report: dict, manifest: dict) -> str:
    lines = [
        "# Similar complaint retrieval evaluation",
        "",
        f"Source: `{manifest.get('data_source', 'not recorded')}` "
        f"({manifest.get('data_source_type', 'unspecified')}); embedder "
        f"`{manifest['embedder_arg']}`.",
        "",
        f"Temporal corpus: {report['n_retrieval_docs']:,} train documents ending "
        f"{report['split']['train_max_date']}; {report['n_queries']:,} sampled queries "
        f"from strictly later complaints ({report['split']['test_min_date']} to "
        f"{report['split']['test_max_date']}).",
        "",
        "**Relevance is a proxy, not human judgment:** a result is counted relevant when its "
        "product and issue match the query complaint. This measures taxonomy similarity, not "
        "whether the result is useful precedent or semantically similar.",
        "",
        f"**Embedding limitation:** {report['embedder_note']}",
        "",
        f"Boundary-date test rows excluded: {report['split']['same_boundary_date_excluded']}; "
        f"cross-split template queries excluded: "
        f"{report['split']['cross_split_template_queries_excluded']}; duplicate test templates "
        f"excluded: {report['split']['duplicate_test_template_queries_excluded']}; queries without "
        f"a training relevance group excluded: "
        f"{report['split']['queries_without_train_relevance_group_excluded']}.",
        "",
        "| Mode | Hit@1 | Hit@5 | Hit@10 | P@1 | P@5 | P@10 | MRR@10 | nDCG@5 | nDCG@10 | "
        "Search p50 ms | Search p95 ms | Query encode p50 ms | End-to-end p50 ms | End-to-end p95 ms |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for mode, values in report["modes"].items():
        lines.append(
            f"| {mode} | {values['hit@1']:.3f} | {values['hit@5']:.3f} | "
            f"{values['hit@10']:.3f} | {values['p@1']:.3f} | {values['p@5']:.3f} | "
            f"{values['p@10']:.3f} | "
            f"{values['mrr@10']:.3f} | {values['ndcg@5']:.3f} | {values['ndcg@10']:.3f} | "
            f"{values['search_latency_ms']['p50']} | {values['search_latency_ms']['p95']} | "
            f"{values['query_embedding_latency_ms']['p50']} | "
            f"{values['end_to_end_latency_ms']['p50']} | "
            f"{values['end_to_end_latency_ms']['p95']} |"
        )
    lines.extend([
        "",
        "## Leakage and reproducibility",
        "",
        "* The retrieval index contains train-split documents only; queries come from later dates.",
        "* Rows on the shared train/test boundary date and exact normalized template duplicates "
        "across the split are excluded.",
        "* The full deterministic query ID list and SHA-256 digest are recorded in the JSON report.",
        "* No genuine relevance judgments are present; do not interpret proxy scores as retrieval "
        "accuracy or verified precedent quality.",
        f"* BM25 index build time: {report['index_build_ms']['bm25']} ms. Dense vectors were "
        "precomputed by the artifact build; query embedding latency is reported separately.",
    ])
    return "\n".join(lines) + "\n"


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
