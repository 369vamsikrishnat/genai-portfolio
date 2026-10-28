"""Scale ladder: memory, build time, recall vs exact search and p50/p95/p99 for float32/int8/binary."""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np

from .. import quant
from ..metrics import percentiles


def synthetic_vectors(n: int, dim: int = 384, clusters: int = 200, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    centers = rng.normal(size=(clusters, dim)).astype(np.float32)
    x = centers[rng.integers(clusters, size=n)] + 0.6 * rng.normal(size=(n, dim)).astype(np.float32)
    return (x / np.linalg.norm(x, axis=1, keepdims=True)).astype(np.float32)


def _timed(fn, items):
    lat, res = [], []
    for i in items:
        t0 = time.perf_counter()
        res.append(fn(i))
        lat.append((time.perf_counter() - t0) * 1000)
    return res, lat


def _recall(exact, approx) -> float:
    return round(float(np.mean([quant.recall_at_k(e, a) for e, a in zip(exact, approx, strict=True)])), 4)


def run_size(db: np.ndarray, queries: np.ndarray, k: int = 10, oversample: int = 10) -> dict:
    n, dim = db.shape
    mem = quant.memory_bytes(n, dim)
    pos = list(range(len(queries)))
    exact, lat_f = _timed(lambda i: quant.topk_float(db, queries[i], k), pos)
    out = {"n": n, "dim": dim, "memory_mb": {m: round(b / 2**20, 2) for m, b in mem.items()},
           "float32": {"recall@k": 1.0, "latency_ms": percentiles(lat_f), "build_s": 0.0}}

    t0 = time.perf_counter()
    db8, scale = quant.to_int8(db)
    b8 = time.perf_counter() - t0
    r8, lat8 = _timed(lambda i: quant.topk_int8(db8, queries[i], scale, k), pos)
    out["int8"] = {"recall@k": _recall(exact, r8), "latency_ms": percentiles(lat8), "build_s": round(b8, 3)}

    t0 = time.perf_counter()
    dbb = quant.to_binary(db)
    bb = time.perf_counter() - t0
    qb = quant.to_binary(queries)
    rb, latb = _timed(lambda i: quant.topk_binary(dbb, qb[i], k), pos)
    out["binary"] = {"recall@k": _recall(exact, rb), "latency_ms": percentiles(latb), "build_s": round(bb, 3)}
    rr, latr = _timed(lambda i: quant.topk_binary_rescore(dbb, db8, qb[i], queries[i], k, oversample, scale), pos)
    out["binary+int8_rescore"] = {"recall@k": _recall(exact, rr), "latency_ms": percentiles(latr),
                                  "build_s": round(bb + b8, 3)}
    try:  # optional: HNSW via FAISS (pip install .[faiss]); not exercised by the test suite
        import faiss

        t0 = time.perf_counter()
        idx = faiss.IndexHNSWFlat(dim, 32, faiss.METRIC_INNER_PRODUCT)
        idx.hnsw.efConstruction = 100
        idx.add(db)
        bh = time.perf_counter() - t0
        idx.hnsw.efSearch = 64
        rh, lath = _timed(lambda i: idx.search(queries[i][None, :], k)[1][0], pos)
        out["faiss_hnsw"] = {"recall@k": _recall(exact, rh), "latency_ms": percentiles(lath),
                             "build_s": round(bh, 2)}
    except ImportError:
        pass
    return out


def run_ladder(vectors: np.ndarray | None, sizes: list[int], n_queries: int = 200, k: int = 10,
               seed: int = 0) -> dict:
    synthetic = vectors is None
    dim = 384 if synthetic else vectors.shape[1]
    results = []
    for n in sizes:
        if synthetic:
            allv = synthetic_vectors(n + n_queries, dim, seed=seed)
        else:
            if n + n_queries > len(vectors):
                continue
            allv = vectors[: n + n_queries]
        qidx = np.random.default_rng(seed).choice(len(allv), n_queries, replace=False)
        mask = np.ones(len(allv), bool)
        mask[qidx] = False
        results.append(run_size(np.ascontiguousarray(allv[mask][:n]), allv[qidx], k))
    return {"synthetic_vectors": synthetic, "k": k, "n_queries": n_queries, "ladder": results}


def to_markdown(res: dict) -> str:
    head = ["| N | variant | memory MB | recall@k vs exact | p50 ms | p95 ms | p99 ms | build s |",
            "|---|---|---|---|---|---|---|---|"]
    rows = []
    for r in res["ladder"]:
        for v in ("float32", "int8", "binary", "binary+int8_rescore", "faiss_hnsw"):
            if v not in r:
                continue
            mem = r["memory_mb"].get(v.split("+")[0], r["memory_mb"]["float32"])
            lt = r[v]["latency_ms"]
            rows.append(f"| {r['n']:,} | {v} | {mem} | {r[v]['recall@k']:.3f} | {lt['p50']} | {lt['p95']} | "
                        f"{lt['p99']} | {r[v]['build_s']} |")
    note = ("\nSingle-threaded numpy brute force unless noted. Memory for `binary+int8_rescore` shows the binary "
            "index only (the int8 vectors used for rescoring must also be kept). Recall is vs exact float32.\n")
    if res["synthetic_vectors"]:
        note += "\n> WARNING: synthetic random vectors. Re-run on your real embeddings for valid results.\n"
    return "\n".join(head + rows) + note


def save(res: dict, results_dir: Path, docs_dir: Path) -> None:
    results_dir.mkdir(parents=True, exist_ok=True)
    docs_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / "scale.json").write_text(json.dumps(res, indent=2))
    (docs_dir / "scale.md").write_text("# Scale ladder\n\n" + to_markdown(res))
