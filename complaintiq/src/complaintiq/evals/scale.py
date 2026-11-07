"""Scale ladder: memory, build time, recall vs exact search and p50/p95/p99 for float32/int8/binary."""
from __future__ import annotations

import dataclasses
import gc
import json
import os
import platform
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from .. import quant
from ..audit import AuditLog
from ..config import Settings
from ..llm import MockLLM, estimate_tokens
from ..metrics import percentiles
from ..pipeline import Artifacts
from ..retrieve import BM25, HybridRetriever, LexicalReranker


def _process_memory_mb() -> dict[str, float | None]:
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        class ProcessMemoryCounters(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD),
                ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
                ("PrivateUsage", ctypes.c_size_t),
            ]

        counters = ProcessMemoryCounters()
        counters.cb = ctypes.sizeof(counters)
        kernel32 = ctypes.WinDLL("Kernel32.dll", use_last_error=True)
        psapi = ctypes.WinDLL("Psapi.dll", use_last_error=True)
        kernel32.GetCurrentProcess.restype = wintypes.HANDLE
        get_memory_info = psapi.GetProcessMemoryInfo
        get_memory_info.argtypes = [
            wintypes.HANDLE, ctypes.POINTER(ProcessMemoryCounters), wintypes.DWORD,
        ]
        get_memory_info.restype = wintypes.BOOL
        ok = get_memory_info(
            kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb
        )
        if ok:
            return {
                "working_set_mb": round(counters.WorkingSetSize / 2**20, 2),
                "peak_working_set_mb": round(counters.PeakWorkingSetSize / 2**20, 2),
                "private_bytes_mb": round(counters.PrivateUsage / 2**20, 2),
            }
    return {"working_set_mb": None, "peak_working_set_mb": None, "private_bytes_mb": None}


def _system_memory_gib() -> float | None:
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        class MemoryStatus(ctypes.Structure):
            _fields_ = [
                ("dwLength", wintypes.DWORD),
                ("dwMemoryLoad", wintypes.DWORD),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        status = MemoryStatus()
        status.dwLength = ctypes.sizeof(status)
        kernel32 = ctypes.WinDLL("Kernel32.dll", use_last_error=True)
        global_memory_status = kernel32.GlobalMemoryStatusEx
        global_memory_status.argtypes = [ctypes.POINTER(MemoryStatus)]
        global_memory_status.restype = wintypes.BOOL
        if global_memory_status(ctypes.byref(status)):
            return round(status.ullTotalPhys / 2**30, 2)
    try:
        return round(os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 2**30, 2)
    except (AttributeError, OSError, ValueError):
        return None


def _timed_batch(fn, repeats: int = 3) -> tuple[dict[str, float], float]:
    fn()
    latencies = []
    for _ in range(repeats):
        started = time.perf_counter()
        fn()
        latencies.append((time.perf_counter() - started) * 1000)
    return percentiles(latencies), float(np.mean(latencies))


def run_real_benchmark(
    art: Artifacts,
    source_path: str | Path,
    settings: Settings,
    sizes: list[int],
    ingest_sizes: list[int],
    n_queries: int = 50,
    api_requests: int = 25,
    concurrency: tuple[int, ...] = (1, 2, 4),
    seed: int = 0,
) -> dict:
    """Measure serving and replay workloads on real trained vectors and metadata."""
    from ..data import load_complaints
    from ..replay import replay

    memory_before = _process_memory_mb()
    n_train = int(art.manifest["n_train"])
    if not 0 < n_train < len(art.meta) or len(art.vectors) != len(art.meta):
        raise ValueError("benchmark requires aligned real artifacts with a temporal train/test split")
    if not sizes or any(n <= 0 or n > n_train for n in sizes):
        raise ValueError(f"workload sizes must be between 1 and n_train={n_train}")
    if not ingest_sizes or any(size <= 0 for size in ingest_sizes):
        raise ValueError("ingestion workload sizes must be positive")
    if n_queries <= 0 or api_requests <= 0 or not concurrency or any(c <= 0 for c in concurrency):
        raise ValueError("query, API request, and concurrency workloads must be positive")

    source = Path(source_path)
    ingestion = []
    if source.exists():
        for size in ingest_sizes:
            started = time.perf_counter()
            loaded = load_complaints(source, only_narrative=True, limit=size, seed=seed)
            elapsed = time.perf_counter() - started
            ingestion.append({
                "requested_rows": size,
                "loaded_rows": len(loaded),
                "seconds": round(elapsed, 4),
                "rows_per_second": round(len(loaded) / elapsed, 2) if elapsed else None,
            })
            del loaded
            gc.collect()
    else:
        ingestion = [{"requested_rows": n, "status": "source path not found"} for n in ingest_sizes]

    classification = []
    for size in sizes:
        vecs = art.vectors[:size]
        latency, mean_ms = _timed_batch(lambda: art.clf.predict_with_conf(vecs), repeats=25)
        classification.append({
            "rows": size,
            "batch_latency_ms": latency,
            "mean_batch_latency_ms": round(mean_ms, 3),
            "rows_per_second": round(size / (mean_ms / 1000), 2) if mean_ms else None,
            "process_memory_after_mb": _process_memory_mb(),
        })

    test_positions = np.arange(n_train, len(art.meta))
    rng = np.random.default_rng(seed)
    selected = rng.choice(test_positions, size=min(n_queries, len(test_positions)), replace=False)
    query_vectors = art.vectors[selected]
    query_texts = art.meta.iloc[selected]["narrative"].astype(str).tolist()
    quantization = []
    retrieval = []
    retrieval_modes = ("bm25", "dense", "rrf", "rrf_rerank")
    for size in sizes:
        database = np.ascontiguousarray(art.vectors[:size])
        quant_result = run_size(database, query_vectors, k=10)
        quant_result["process_memory_after_mb"] = _process_memory_mb()
        quantization.append(quant_result)

        texts = art.meta.iloc[:size]["narrative"].astype(str).tolist()
        build_started = time.perf_counter()
        bm25 = BM25().fit(texts)
        index_build_s = time.perf_counter() - build_started
        retriever = HybridRetriever(texts, database, art.embedder, bm25, LexicalReranker())
        for mode in retrieval_modes:
            query_latencies = []
            for query in query_texts:
                started = time.perf_counter()
                retriever.search(query, k=5, mode=mode, need_dense_score=mode != "bm25")
                query_latencies.append((time.perf_counter() - started) * 1000)
            retrieval.append({
                "index_rows": size,
                "index_build_seconds": round(index_build_s, 3),
                "query_latency_ms": percentiles(query_latencies),
                "queries_per_second": round(
                    len(query_latencies) / (sum(query_latencies) / 1000), 2
                ) if sum(query_latencies) else None,
                "mode": mode,
                "query_source": "temporal artifact test split",
                "n_queries": len(query_latencies),
            })
        del retriever, bm25, texts, database
        gc.collect()

    replay_times: list[float] = []
    replay_rows = 0

    def replay_handler(batch):
        nonlocal replay_rows
        started = time.perf_counter()
        vectors = art.embedder.encode(batch["narrative"].astype(str).tolist())
        art.clf.predict_with_conf(vectors)
        replay_times.append((time.perf_counter() - started) * 1000)
        replay_rows += len(batch)

    replay_started = time.perf_counter()
    replay_stats = replay(art.meta, replay_handler)
    replay_elapsed = time.perf_counter() - replay_started

    from ..api.app import create_app
    from ..service import Service
    from fastapi.testclient import TestClient

    bench_settings = dataclasses.replace(
        settings, rate_limit_per_min=100_000, api_key="",
    )
    service = Service(art, MockLLM(), bench_settings, audit=AuditLog())
    app = create_app(service, bench_settings)
    client = TestClient(app)
    request_text = (
        "I found a transfer I did not authorize on my financial account. "
        "Please explain the review process and available options."
    )
    api_latencies = []
    api_statuses: dict[str, int] = {}
    api_cost_estimates = []
    api_started = time.perf_counter()
    for index in range(api_requests):
        started = time.perf_counter()
        response = client.post(
            "/triage", json={"text": request_text},
            headers={"X-Request-ID": f"perf-sequential-{index}"},
        )
        api_latencies.append((time.perf_counter() - started) * 1000)
        api_statuses[str(response.status_code)] = api_statuses.get(str(response.status_code), 0) + 1
        if response.status_code == 200:
            api_cost_estimates.append(float(response.json()["est_cost_usd"]))
    api_sequential_elapsed = time.perf_counter() - api_started

    concurrency_results = []
    for workers in concurrency:
        total_requests = api_requests * workers
        started_all = time.perf_counter()

        def request(index):
            started = time.perf_counter()
            response = client.post(
                "/triage", json={"text": request_text},
                headers={"X-Request-ID": f"perf-{workers}-{index}"},
            )
            return (time.perf_counter() - started) * 1000, response.status_code

        with ThreadPoolExecutor(max_workers=workers) as pool:
            results = list(pool.map(request, range(total_requests)))
        elapsed = time.perf_counter() - started_all
        latencies = [item[0] for item in results]
        statuses: dict[str, int] = {}
        for _, status in results:
            statuses[str(status)] = statuses.get(str(status), 0) + 1
        concurrency_results.append({
            "workers": workers,
            "requests": total_requests,
            "wall_seconds": round(elapsed, 4),
            "requests_per_second": round(total_requests / elapsed, 2) if elapsed else None,
            "latency_ms": percentiles(latencies),
            "statuses": statuses,
        })
    client.close()

    prompt_tokens = estimate_tokens(request_text) + 64
    completion_tokens = 24
    assumed_escalated_cost = (
        prompt_tokens * settings.price_in_per_m + completion_tokens * settings.price_out_per_m
    ) / 1_000_000
    memory_after = _process_memory_mb()
    return {
        "evaluation_type": "real_artifact_performance_benchmark",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "seed": seed,
        "artifact": {
            "data_source_type": art.manifest.get("data_source_type", "real CFPB; manifest field unavailable"),
            "rows": len(art.meta),
            "training_rows": n_train,
            "test_rows": len(art.meta) - n_train,
            "dimensions": int(art.vectors.shape[1]),
            "embedder": art.manifest.get("embedder_arg", "unknown"),
            "artifact_version": art.manifest.get("artifact_version", art.manifest.get("built_at")),
        },
        "configuration": {
            "source_path": str(source.resolve()),
            "workload_sizes": sizes,
            "ingestion_sizes": ingest_sizes,
            "n_queries": len(query_texts),
            "api_requests_per_worker_level": api_requests,
            "concurrency_levels": list(concurrency),
            "classifier_batch_timing": {"warmup_batches": 1, "measured_batches": 25},
            "quantization_k": 10,
            "retrieval_modes": list(retrieval_modes),
            "replay": "monthly artifact batches; hashing embed and classifier predict",
            "hardware": {
                "platform": platform.platform(),
                "processor": platform.processor() or os.environ.get("PROCESSOR_IDENTIFIER", "unknown"),
                "logical_cpus": os.cpu_count(),
                "memory_gib": _system_memory_gib(),
                "python": platform.python_version(),
            },
            "runtime_versions": {
                "numpy": np.__version__,
                "pandas": __import__("pandas").__version__,
                "scikit_learn": __import__("sklearn").__version__,
                "scipy": __import__("scipy").__version__,
            },
        },
        "ingestion": {
            "method": "load_complaints from processed Parquet with deterministic sample limits",
            "source_rows_returned": ingestion,
        },
        "classification": {
            "batch_workloads": classification,
            "single_record_latency_ms": _measure_single_classification(art, selected),
        },
        "retrieval": retrieval,
        "quantization": quantization,
        "replay": {
            "records_processed": replay_rows,
            "months": len(replay_stats),
            "wall_seconds": round(replay_elapsed, 4),
            "records_per_second": round(replay_rows / replay_elapsed, 2) if replay_elapsed else None,
            "monthly_batch_latency_ms": percentiles(replay_times),
        },
        "api": {
            "sequential_requests": api_requests,
            "sequential_wall_seconds": round(api_sequential_elapsed, 4),
            "sequential_requests_per_second": round(
                api_requests / api_sequential_elapsed, 2
            ) if api_sequential_elapsed else None,
            "sequential_latency_ms": percentiles(api_latencies),
            "sequential_statuses": api_statuses,
            "concurrency": concurrency_results,
        },
        "cost": {
            "measured_external_spend_usd": 0.0,
            "measured_llm_provider": "MockLLM; no external model calls",
            "measured_api_mock_est_cost_mean_usd": round(float(np.mean(api_cost_estimates)), 8)
            if api_cost_estimates else 0.0,
            "assumption_based_cost_per_escalated_triage_usd": round(assumed_escalated_cost, 8),
            "assumption_based_cost_per_1000_escalated_triages_usd": round(
                assumed_escalated_cost * 1000, 4
            ),
            "assumptions": {
                "input_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "price_in_per_m_usd": settings.price_in_per_m,
                "price_out_per_m_usd": settings.price_out_per_m,
                "draft_generation_external_llm_calls": 0,
                "note": "Price-list scenario only; no external provider spend was measured.",
            },
        },
        "memory": {
            "before_mb": memory_before,
            "after_mb": memory_after,
            "vector_storage_bytes": quant.memory_bytes(len(art.meta), art.vectors.shape[1]),
            "quantized_sizes": [
                {"rows": entry["n"], "reported_memory_mb": entry["memory_mb"]}
                for entry in quantization
            ],
        },
        "limitations": [
            "Benchmark ran on one local laptop, one Python process, and the sampled/deduplicated real artifact; it does not establish production capacity.",
            "API uses TestClient and MockLLM; network, TLS, remote provider latency, and provider cost are not measured.",
            "Workload sizes are bounded by the current temporal training index; no out-of-sample extrapolation is reported.",
            "Process working-set memory is measured, but per-stage peak memory is not isolated.",
            "Quantization representation sizes estimate deployable vector storage; the benchmark retains float32 and compressed forms simultaneously.",
            "Quantized recall is top-10 overlap against exact float32 on later holdout queries, not human relevance quality.",
        ],
    }


def _measure_single_classification(art: Artifacts, positions: np.ndarray) -> dict[str, float]:
    latencies = []
    for position in positions:
        started = time.perf_counter()
        art.clf.predict_with_conf(art.vectors[position:position + 1])
        latencies.append((time.perf_counter() - started) * 1000)
    return percentiles(latencies)


def benchmark_to_markdown(report: dict) -> str:
    lines = [
        "# ComplaintIQ performance, scalability, and cost evaluation",
        "",
        f"Artifact: {report['artifact']['rows']:,} records ({report['artifact']['training_rows']:,} training; "
        f"{report['artifact']['test_rows']:,} test), {report['artifact']['dimensions']} dimensions, "
        f"`{report['artifact']['embedder']}`. Hardware: {report['configuration']['hardware']}.",
        "",
        "## Processed-source load throughput",
        "",
        "| Requested rows | Loaded rows | seconds | rows/s |",
        "|---:|---:|---:|---:|",
    ]
    for row in report["ingestion"]["source_rows_returned"]:
        lines.append(
            f"| {row['requested_rows']:,} | {row.get('loaded_rows', 'n/a')} | "
            f"{row.get('seconds', 'n/a')} | {row.get('rows_per_second', 'n/a')} |"
        )
    lines.extend([
        "",
        "## Classification",
        "",
        "| Batch rows | p50 ms | p95 ms | p99 ms | rows/s |",
        "|---:|---:|---:|---:|---:|",
    ])
    for row in report["classification"]["batch_workloads"]:
        lat = row["batch_latency_ms"]
        lines.append(
            f"| {row['rows']:,} | {lat['p50']} | {lat['p95']} | {lat['p99']} | {row['rows_per_second']} |"
        )
    lines.extend([
        "",
        f"Single-record classification p50/p95/p99: "
        f"{report['classification']['single_record_latency_ms']}.",
        "",
        "## Retrieval",
        "",
        "Dense retrieval is exact NumPy dot product over saved vectors (no ANN index build); query latency "
        "includes query encoding for dense/hybrid modes and omits it for BM25.",
        "",
        "| Index rows | mode | BM25 build s | p50 ms | p95 ms | p99 ms | queries/s |",
        "|---:|---|---:|---:|---:|---:|---:|",
    ])
    for row in report["retrieval"]:
        lat = row["query_latency_ms"]
        lines.append(
            f"| {row['index_rows']:,} | {row['mode']} | {row['index_build_seconds']} | {lat['p50']} | "
            f"{lat['p95']} | {lat['p99']} | {row['queries_per_second']} |"
        )
    lines.extend([
        "",
        "## Quantization",
        "",
        "| Rows | Representation | memory MB | recall@10 vs float32 | p50 ms | p95 ms | p99 ms | build s |",
        "|---:|---|---:|---:|---:|---:|---:|---:|",
    ])
    variants = ("float32", "int8", "binary", "binary+int8_rescore", "faiss_hnsw")
    for entry in report["quantization"]:
        for variant in variants:
            if variant not in entry:
                continue
            lat = entry[variant]["latency_ms"]
            memory = entry["memory_mb"].get(variant, "n/a")
            lines.append(
                f"| {entry['n']:,} | {variant} | {memory} | "
                f"{entry[variant]['recall@k']} | {lat['p50']} | {lat['p95']} | "
                f"{lat['p99']} | {entry[variant]['build_s']} |"
            )
    replay = report["replay"]
    lines.extend([
        "",
        "## Monthly replay",
        "",
        f"Processed {replay['records_processed']:,} artifact records across {replay['months']} months "
        f"in {replay['wall_seconds']} s ({replay['records_per_second']} records/s). "
        f"Monthly batch p50/p95/p99 latency: {replay['monthly_batch_latency_ms']}.",
        "",
        "## API and concurrency",
        "",
        f"Sequential TestClient p50/p95/p99 latency: {report['api']['sequential_latency_ms']}; "
        f"throughput: {report['api']['sequential_requests_per_second']} requests/s. "
        f"Statuses: {report['api']['sequential_statuses']}.",
        "",
        "| Workers | Requests | requests/s | p50 ms | p95 ms | p99 ms | statuses |",
        "|---:|---:|---:|---:|---:|---:|---|",
    ])
    for row in report["api"]["concurrency"]:
        lat = row["latency_ms"]
        lines.append(
            f"| {row['workers']} | {row['requests']} | {row['requests_per_second']} | "
            f"{lat['p50']} | {lat['p95']} | {lat['p99']} | {row['statuses']} |"
        )
    cost = report["cost"]
    lines.extend([
        "",
        "## Memory and cost",
        "",
        f"Process working set before/after: {report['memory']['before_mb']} / "
        f"{report['memory']['after_mb']} MB (peak: "
        f"{report['memory']['after_mb']['peak_working_set_mb']} MB). Vector storage estimates "
        "(per representation, not aggregate benchmark-process memory): "
        f"{report['memory']['vector_storage_bytes']}.",
        f"Measured external spend: ${cost['measured_external_spend_usd']:.2f} "
        f"(MockLLM; no external provider calls). Mock per-request estimates are not spend. "
        f"At assumed {cost['assumptions']['input_tokens']} input / "
        f"{cost['assumptions']['completion_tokens']} output tokens and configured prices, "
        f"scenario cost is ${cost['assumption_based_cost_per_escalated_triage_usd']:.6f} per "
        f"escalated triage (${cost['assumption_based_cost_per_1000_escalated_triages_usd']:.4f}/1k). "
        "The evidence-template draft path makes zero external model calls.",
        "",
        "## Limitations",
        "",
    ])
    lines.extend(f"* {item}" for item in report["limitations"])
    return "\n".join(lines) + "\n"


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
    memory_mb = {name: round(size / 2**20, 2) for name, size in mem.items()}
    memory_mb["binary+int8_rescore"] = round(
        (mem["binary"] + mem["int8"]) / 2**20, 2
    )
    pos = list(range(len(queries)))
    exact, lat_f = _timed(lambda i: quant.topk_float(db, queries[i], k), pos)
    out = {"n": n, "dim": dim, "memory_mb": memory_mb,
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
    note = ("\nSingle-threaded numpy brute force unless noted. `binary+int8_rescore` includes both binary "
            "and int8 vector storage. Recall is vs exact float32.\n")
    if res["synthetic_vectors"]:
        note += "\n> WARNING: synthetic random vectors. Re-run on your real embeddings for valid results.\n"
    return "\n".join(head + rows) + note


def save(res: dict, results_dir: Path, docs_dir: Path) -> None:
    results_dir.mkdir(parents=True, exist_ok=True)
    docs_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / "scale.json").write_text(json.dumps(res, indent=2))
    (docs_dir / "scale.md").write_text("# Scale ladder\n\n" + to_markdown(res))
