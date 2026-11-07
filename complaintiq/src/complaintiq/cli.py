"""Command line: python -m complaintiq <command> --help"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np

from .config import Settings


def _art(s: Settings):
    from .pipeline import Artifacts

    if not Artifacts.exists(s.artifacts_dir):
        raise SystemExit(f"no artifacts in {s.artifacts_dir}. Run `python -m complaintiq build` "
                         "(or `ensure-artifacts` for a synthetic demo).")
    return Artifacts.load(s.artifacts_dir)


def cmd_synth(a, s):
    from .synth import generate

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    df = generate(a.n, seed=a.seed)
    df.to_csv(out, index=False)
    print(f"wrote {len(df)} synthetic complaints -> {out}  (NOT real data: for smoke tests only)")


def cmd_download(a, s):
    from .ingest import download

    print("downloading CFPB bulk file (large; this takes a while)...")
    print("saved:", download(a.out))


def cmd_ingest(a, s):
    from .ingest import ingest

    res = ingest(a.src, a.out, since_year=a.since, keep_without_narrative=a.keep_blank,
                 narratives=a.narratives or None)
    s.results_dir.mkdir(parents=True, exist_ok=True)
    (s.results_dir / "ingest_stats.json").write_text(json.dumps(res, indent=2))
    print(json.dumps(res, indent=2))


def cmd_inspect_archive(a, s):
    from .archive import expand_inputs, inspect

    for p in expand_inputs(a.path)[: a.max_files]:
        print(json.dumps(inspect(p), indent=2, default=str))


def cmd_report(a, s):
    from .data import load_complaints
    from .report import build_report, to_markdown

    df = load_complaints(a.src, since_year=a.since, only_narrative=True, limit=a.sample)
    stats = s.results_dir / "ingest_stats.json"
    totals = json.loads(stats.read_text()) if stats.exists() else {}
    note = f"Computed on a {len(df):,}-row deterministic sample." if a.sample else "Computed on all rows."
    rep = build_report(df, totals, note)
    s.results_dir.mkdir(parents=True, exist_ok=True)
    s.docs_dir.mkdir(parents=True, exist_ok=True)
    (s.results_dir / "data_quality.json").write_text(json.dumps(rep, indent=2, default=str))
    md = to_markdown(rep)
    (s.docs_dir / "data_quality.md").write_text(md)
    print(md)


def cmd_build(a, s):
    from .pipeline import build

    source_type = "synthetic" if Path(a.src).stem.casefold() == "synth" else "real_cfpb"
    m = build(a.src, a.out or s.artifacts_dir, sample=a.sample, since_year=a.since,
              embedder_name=a.embedder or s.embedder, max_chars=s.max_chars,
              data_source_type=source_type, test_cutoff=a.test_cutoff,
              classifier_only=a.classifier_only)
    print(json.dumps(m, indent=2))


def cmd_ensure(a, s):
    from .pipeline import Artifacts, build
    from .synth import generate

    if Artifacts.exists(s.artifacts_dir):
        return print("artifacts present")
    p = s.data_dir / "synth.csv"
    p.parent.mkdir(parents=True, exist_ok=True)
    if not p.exists():
        generate(a.n).to_csv(p, index=False)
    print(json.dumps(build(p, s.artifacts_dir, embedder_name="hashing",
                           data_source_type="synthetic"), indent=2))


def cmd_eval_retrieval(a, s):
    from .evals.retrieval import run_temporal_evaluation, temporal_to_markdown

    art = _art(s)
    res = run_temporal_evaluation(art, n_queries=a.n_queries, seed=a.seed)
    md = temporal_to_markdown(res, art.manifest)
    s.results_dir.mkdir(parents=True, exist_ok=True)
    s.docs_dir.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(res, indent=2)
    (s.results_dir / "retrieval_ablation.json").write_text(payload)
    (s.results_dir / "retrieval_evaluation.json").write_text(payload)
    (s.results_dir / "retrieval_evaluation.md").write_text(md)
    (s.docs_dir / "ablation.md").write_text(md)
    print(md)


def cmd_eval_cascade(a, s):
    from .classify import LLMRun, cost_table_markdown, evaluate_cascade, run_llm_labels
    from .llm import Usage, get_llm

    if a.batch_size < 1:
        raise SystemExit("--batch-size must be at least 1")

    art = _art(s)
    n_train = int(art.manifest["n_train"])
    lab = art.manifest["label_col"]
    test = art.meta.iloc[n_train:]
    rng = np.random.default_rng(0)
    pick = rng.choice(len(test), size=min(a.n, len(test)), replace=False)
    texts = test["narrative"].to_numpy()[pick].tolist()
    y = test[lab].to_numpy()[pick]
    X = art.vectors[n_train:][pick]

    t0 = time.perf_counter()
    pred, conf = art.clf.predict_with_conf(X)
    clf_ms = (time.perf_counter() - t0) * 1000 / len(pick)

    simulated = s.llm_provider == "mock"
    truth = {t[:1500].strip(): str(g) for t, g in zip(texts, y, strict=True)} if simulated else None
    if simulated:
        print("WARNING: CIQ_LLM=mock -> LLM is SIMULATED; cost-table numbers are not results.")

    s.results_dir.mkdir(parents=True, exist_ok=True)
    s.docs_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = s.results_dir / "cascade_checkpoint.json"
    signature = {
        "n": len(pick),
        "sample_indices": [int(i) for i in pick],
        "n_train": n_train,
        "test_rows": len(test),
        "label_col": str(lab),
        "data_source": art.manifest.get("data_source"),
        "provider": s.llm_provider,
        "price_in": s.price_in_per_m,
        "price_out": s.price_out_per_m,
    }

    llm = get_llm(s, truth)
    labels = [str(c) for c in art.clf.classes_]

    if checkpoint_path.exists():
        state = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        if state.get("signature") != signature:
            raise SystemExit(
                f"Checkpoint {checkpoint_path} belongs to a different sample/configuration. "
                "Move or delete it to start a fresh evaluation."
            )
        preds = state["preds"]
        costs = state["costs"]
        lats = state["latencies_ms"]
        usages = [Usage(**u) for u in state["usage"]]
        completed = int(state["completed"])
        if not (len(preds) == len(costs) == len(lats) == len(usages) == completed):
            raise SystemExit("Checkpoint is inconsistent; it was left untouched.")
        if completed > len(pick):
            raise SystemExit("Checkpoint contains more rows than this evaluation.")
        if hasattr(llm, "models_used"):
            llm.models_used.update(state.get("models_used", []))
        if state.get("llm_model") and hasattr(llm, "model"):
            llm.model = state["llm_model"]
        if state.get("llm_name"):
            llm.name = state["llm_name"]
        print(f"Resuming: {completed}/{len(pick)} complaints already saved.")
    else:
        preds, costs, lats, usages = [], [], [], []
        completed = 0

    def save_checkpoint(done):
        payload = {
            "version": 1,
            "signature": signature,
            "completed": done,
            "preds": preds,
            "costs": costs,
            "latencies_ms": lats,
            "usage": [
                {"prompt_tokens": u.prompt_tokens, "completion_tokens": u.completion_tokens}
                for u in usages
            ],
            "llm_name": llm.name,
            "llm_model": getattr(llm, "model", None),
            "models_used": sorted(getattr(llm, "models_used", set())),
        }
        temp_path = checkpoint_path.with_suffix(".json.tmp")
        temp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        temp_path.replace(checkpoint_path)

    for start in range(completed, len(pick), a.batch_size):
        end = min(start + a.batch_size, len(pick))
        print(f"Processing complaints {start + 1}-{end} of {len(pick)}...", flush=True)
        batch = run_llm_labels(
            llm, texts[start:end], labels, s.price_in_per_m, s.price_out_per_m
        )
        preds.extend(batch.preds)
        costs.extend(batch.costs)
        lats.extend(batch.latencies_ms)
        usages.extend(batch.usage)
        completed = end
        save_checkpoint(completed)
        print(f"Checkpoint saved: {completed}/{len(pick)} completed.", flush=True)

    run = LLMRun(preds, costs, lats, usages)
    rows = evaluate_cascade(y, pred, conf, run, a.thresholds, clf_ms)
    meta = {
        "n": len(pick),
        "llm": llm.name,
        "models_used": sorted(getattr(llm, "models_used", set())),
        "price_in": s.price_in_per_m,
        "price_out": s.price_out_per_m,
        "simulated": simulated,
        "batch_size": a.batch_size,
        "checkpoint": str(checkpoint_path),
    }
    md = cost_table_markdown(rows, meta)
    (s.results_dir / "cascade.json").write_text(
        json.dumps({"rows": rows, "meta": meta}, indent=2), encoding="utf-8"
    )
    (s.docs_dir / "cost_table.md").write_text(
        "# Cascade cost table\n\n" + md, encoding="utf-8"
    )
    print(md)

def cmd_eval_classifier(a, s):
    from .classifier_metrics import evaluate_classifier, to_markdown

    art = _art(s)
    n_train = int(art.manifest["n_train"])
    if len(art.vectors) != len(art.meta):
        raise ValueError("artifact vectors and metadata have different row counts")
    if not 0 <= n_train < len(art.meta):
        raise ValueError(f"invalid temporal split: n_train={n_train}, rows={len(art.meta)}")

    label_col = art.manifest["label_col"]
    y_test = art.meta[label_col].iloc[n_train:].to_numpy()
    report = evaluate_classifier(art.clf, art.vectors[n_train:], y_test,
                                 min_support=a.min_support)
    report["data_source"] = art.manifest.get("data_source")
    report["data_source_type"] = art.manifest.get("data_source_type", "unspecified")
    report["sampled_rows"] = art.manifest.get("sample") or art.manifest["n"]
    report["artifact_rows"] = art.manifest["n"]
    report["label_col"] = label_col
    report["temporal_split"] = art.manifest.get("temporal_split", {
        "strategy": "chronological", "train_rows": n_train, "test_rows": len(y_test),
    })
    md = to_markdown(report, art.manifest)

    s.results_dir.mkdir(parents=True, exist_ok=True)
    (s.results_dir / "classifier_metrics.json").write_text(json.dumps(report, indent=2))
    (s.results_dir / "classifier_metrics.md").write_text(md)
    print(md)


def cmd_spikes(a, s):
    from .llm import get_llm
    from .spikes import detect_spikes, write_brief

    if a.src:  # full metadata (ingest with --keep-blank): spikes need no narratives
        from .data import load_complaints

        meta = load_complaints(a.src, since_year=a.since, only_narrative=False)
        if "narrative" not in meta.columns:
            meta["narrative"] = ""
        meta["narrative"] = meta["narrative"].fillna("")
    else:
        meta = _art(s).meta
    sp = detect_spikes(meta, keys=("company", "product", "issue"), z_thresh=a.z,
                       min_count=a.min_count, min_baseline_count=a.min_baseline_count)
    llm = get_llm(s) if a.brief else None
    out = []
    for _, r in sp.head(a.top).iterrows():
        d = r.to_dict()
        week = d["week"]
        m = meta
        ex = m[(m.company == d["company"]) & (m.product == d["product"])
               & (m.issue == d["issue"]) & (m.date_received >= week)
               & (m.date_received < week + np.timedelta64(7, "D"))]["narrative"].head(5).tolist()
        d["brief"] = write_brief(d, ex, llm)
        d["week"] = f"{week:%Y-%m-%d}"
        out.append(d)
    s.results_dir.mkdir(parents=True, exist_ok=True)
    (s.results_dir / "spikes.json").write_text(json.dumps(out, indent=2, default=str))
    print(f"{len(sp)} spikes flagged; top {len(out)} saved to results/spikes.json")
    for d in out:
        print("-", d["brief"])


def cmd_eval_spikes(a, s):
    from .spikes import evaluate_historical_spikes, load_weekly_counts, spike_evaluation_markdown

    counts = load_weekly_counts(a.src, keys=("company", "product", "issue"))
    report = evaluate_historical_spikes(
        counts, keys=("company", "product", "issue"), baseline_weeks=a.baseline_weeks,
        z_thresh=a.z, min_count=a.min_count, min_baseline_count=a.min_baseline_count,
    )
    report["data"]["source"] = str(Path(a.src).resolve())
    report["data"]["source_type"] = "processed_parquet" if Path(a.src).is_dir() else "source_file"
    md = spike_evaluation_markdown(report)
    s.results_dir.mkdir(parents=True, exist_ok=True)
    (s.results_dir / "spike_evaluation.json").write_text(json.dumps(report, indent=2))
    (s.results_dir / "spike_evaluation.md").write_text(md)
    print(md)


def cmd_scale(a, s):
    from .evals.scale import run_ladder, save, to_markdown

    vecs = None
    if not a.synthetic:
        vecs = _art(s).vectors
    res = run_ladder(vecs, a.sizes, n_queries=a.n_queries)
    save(res, s.results_dir, s.docs_dir)
    print(to_markdown(res))


def cmd_benchmark(a, s):
    from .evals.scale import benchmark_to_markdown, run_real_benchmark

    report = run_real_benchmark(
        _art(s), a.src, s, a.sizes, a.ingest_sizes, n_queries=a.n_queries,
        api_requests=a.api_requests, concurrency=tuple(a.concurrency), seed=a.seed,
    )
    markdown = benchmark_to_markdown(report)
    s.results_dir.mkdir(parents=True, exist_ok=True)
    (s.results_dir / "performance_evaluation.json").write_text(json.dumps(report, indent=2))
    (s.results_dir / "performance_evaluation.md").write_text(markdown)
    print(markdown)


def cmd_label_sample(a, s):
    from .evals.risk import make_label_sheet

    if a.artifact_holdout:
        art = _art(s)
        df = art.meta.iloc[int(art.manifest["n_train"]):]
    else:
        from .data import load_complaints

        df = load_complaints(a.src, since_year=a.since, only_narrative=True)
    make_label_sheet(df, a.out, n=a.n)
    print(f"wrote {a.out}: fill the risk_flag (0/1) and severity columns by hand, then run eval-risk")


def cmd_eval_risk(a, s):
    from .evals.risk import score_rules, score_to_markdown

    res = score_rules(a.sheet)
    s.results_dir.mkdir(parents=True, exist_ok=True)
    (s.results_dir / "risk_rules.json").write_text(json.dumps(res, indent=2))
    md = score_to_markdown(res)
    (s.results_dir / "risk_rules.md").write_text(md)
    print(md)


def cmd_eval_drafts(a, s):
    from .evals.draft import evaluate_grounded_drafts, to_markdown

    art = _art(s)
    report = evaluate_grounded_drafts(
        art, n_queries=a.n_queries, seed=a.seed, min_dense_score=s.min_dense_score,
    )
    md = to_markdown(report)
    s.results_dir.mkdir(parents=True, exist_ok=True)
    (s.results_dir / "evidence_generation.json").write_text(json.dumps(report, indent=2))
    (s.results_dir / "evidence_generation.md").write_text(md)
    print(md)


def cmd_risk_audit(a, s):
    from .evals.risk import audit_rule_coverage, coverage_to_markdown

    art = _art(s)
    n_train = int(art.manifest["n_train"])
    if not 0 <= n_train < len(art.meta):
        raise ValueError(f"invalid temporal split: n_train={n_train}, rows={len(art.meta)}")
    report = audit_rule_coverage(art.meta.iloc[n_train:], art.manifest)
    md = coverage_to_markdown(report)
    s.results_dir.mkdir(parents=True, exist_ok=True)
    (s.results_dir / "risk_coverage.json").write_text(json.dumps(report, indent=2))
    (s.results_dir / "risk_coverage.md").write_text(md)
    print(md)


def cmd_replay(a, s):
    from .replay import replay

    art = _art(s)
    df = art.meta

    def handler(batch):
        x = art.embedder.encode(batch["narrative"].tolist())
        art.clf.predict_with_conf(x)

    for st in replay(df, handler):
        print(st)


def cmd_demo(a, s):
    from dataclasses import replace

    from .service import Service

    demo_settings = replace(s, artifacts_dir=s.artifacts_dir / "demo")
    cmd_ensure(argparse.Namespace(n=20000), demo_settings)
    svc = Service.from_artifacts(demo_settings)
    text = "Unauthorized charge on my card. I did not make these transactions. I will contact my attorney."
    print(json.dumps(svc.triage(text), indent=2))
    print(json.dumps(svc.draft(text), indent=2, default=str))


def cmd_serve(a, s):
    import uvicorn

    uvicorn.run("complaintiq.api.app:app", host=a.host, port=a.port, workers=a.workers)


def main(argv: list[str] | None = None) -> None:
    s = Settings.from_env()
    p = argparse.ArgumentParser(prog="complaintiq")
    sub = p.add_subparsers(dest="cmd", required=True)

    def add(name, fn, **kw):
        sp = sub.add_parser(name, **kw)
        sp.set_defaults(fn=fn)
        return sp

    x = add("synth", cmd_synth, help="generate synthetic CFPB-shaped data (smoke tests only)")
    x.add_argument("--n", type=int, default=20000); x.add_argument("--seed", type=int, default=0)  # noqa: E702
    x.add_argument("--out", default="data/synth.csv")
    x = add("download", cmd_download, help="download the CFPB bulk zip")
    x.add_argument("--out", default="data/raw")
    x = add("ingest", cmd_ingest, help="zip/csv -> partitioned Parquet (DuckDB)")
    x.add_argument("--src", default="data/raw/complaints.csv.zip"); x.add_argument("--out", default="data/parquet")  # noqa: E702
    x.add_argument("--since", type=int, default=None); x.add_argument("--keep-blank", action="store_true")  # noqa: E702
    x.add_argument("--narratives", nargs="*", default=None,
                   help="CFPB narratives-archive zips/CSVs or a folder (needed: live CFPB file has no narratives)")
    x = add("inspect-archive", cmd_inspect_archive, help="show header/sample of archive files (read-only)")
    x.add_argument("--path", nargs="+", required=True); x.add_argument("--max-files", type=int, default=3)  # noqa: E702
    x = add("report", cmd_report, help="data-quality report -> docs/data_quality.md")
    x.add_argument("--src", default="data/processed"); x.add_argument("--since", type=int, default=None)  # noqa: E702
    x.add_argument("--sample", type=int, default=200_000)
    x = add("build", cmd_build, help="embed + train + index -> artifacts/")
    x.add_argument("--src", default="data/parquet"); x.add_argument("--out", default=None)  # noqa: E702
    x.add_argument("--sample", type=int, default=100_000); x.add_argument("--since", type=int, default=None)  # noqa: E702
    x.add_argument("--embedder", default=None)
    x.add_argument("--test-cutoff", default=None,
                   help="fixed date cutoff; train before this date and test on/after it")
    x.add_argument("--classifier-only", action="store_true",
                   help="skip BM25 index construction")
    x = add("ensure-artifacts", cmd_ensure, help="build a synthetic demo if no artifacts exist")
    x.add_argument("--n", type=int, default=20000)
    x = add("eval-retrieval", cmd_eval_retrieval,
            help="temporal BM25/dense/RRF evaluation (product+issue proxy labels)")
    x.add_argument("--n-queries", type=int, default=500)
    x.add_argument("--seed", type=int, default=0)
    x = add("eval-cascade", cmd_eval_cascade, help="classifier vs LLM vs cascade cost table")
    x.add_argument("--n", type=int, default=300)
    x.add_argument("--batch-size", type=int, default=10)
    x.add_argument("--thresholds", type=float, nargs="+", default=[0.5, 0.6, 0.7, 0.8, 0.9])
    x = add("eval-classifier", cmd_eval_classifier,
            help="evaluate the complete temporal test split -> results/classifier_metrics.*")
    x.add_argument("--min-support", type=int, default=50)
    x = add("eval-drafts", cmd_eval_drafts,
            help="audit evidence grounding on real temporal holdout complaints")
    x.add_argument("--n-queries", type=int, default=100)
    x.add_argument("--seed", type=int, default=0)
    x = add("spikes", cmd_spikes, help="weekly spike detection + briefs")
    x.add_argument("--z", type=float, default=3.0); x.add_argument("--min-count", type=int, default=10)  # noqa: E702
    x.add_argument("--min-baseline-count", type=int, default=20)
    x.add_argument("--top", type=int, default=10); x.add_argument("--brief", action="store_true")  # noqa: E702
    x.add_argument("--src", default=None, help="parquet dir ingested with --keep-blank (all complaints)")
    x.add_argument("--since", type=int, default=None)
    x = add("eval-spikes", cmd_eval_spikes,
            help="chronological unlabeled spike backtest on complete weekly counts")
    x.add_argument("--src", default="data/processed")
    x.add_argument("--baseline-weeks", type=int, default=8)
    x.add_argument("--z", type=float, default=3.0)
    x.add_argument("--min-count", type=int, default=10)
    x.add_argument("--min-baseline-count", type=int, default=20)
    x = add("scale", cmd_scale, help="size ladder: quantisation recall/memory/latency")
    x.add_argument("--sizes", type=int, nargs="+", default=[100_000, 1_000_000])
    x.add_argument("--n-queries", type=int, default=200); x.add_argument("--synthetic", action="store_true")  # noqa: E702
    x = add("benchmark", cmd_benchmark,
            help="real-artifact workload, retrieval, API, replay, memory and cost evaluation")
    x.add_argument("--src", default=str(s.data_dir / "processed"),
                   help="processed CFPB Parquet source for load-throughput measurements")
    x.add_argument("--sizes", type=int, nargs="+", default=[10_000, 25_000, 50_000])
    x.add_argument("--ingest-sizes", type=int, nargs="+", default=[1_000, 5_000, 10_000])
    x.add_argument("--n-queries", type=int, default=50)
    x.add_argument("--api-requests", type=int, default=10)
    x.add_argument("--concurrency", type=int, nargs="+", default=[1, 2, 4])
    x.add_argument("--seed", type=int, default=0)
    x = add("label-sample", cmd_label_sample, help="export a sheet to hand-label risk flags")
    x.add_argument("--src", default="data/parquet"); x.add_argument("--out", default="evals_labels.csv")  # noqa: E702
    x.add_argument("--n", type=int, default=250); x.add_argument("--since", type=int, default=None)  # noqa: E702
    x.add_argument("--artifact-holdout", action="store_true",
                   help="sample the temporal test split from the loaded artifact")
    x = add("eval-risk", cmd_eval_risk, help="score risk rules against your hand labels")
    x.add_argument("--sheet", default="evals_labels.csv")
    add("risk-audit", cmd_risk_audit,
        help="audit rule coverage on the artifact temporal holdout (not labeled performance)")
    add("replay", cmd_replay, help="replay months as batches, print throughput")
    add("demo", cmd_demo, help="synthetic end-to-end demo")
    x = add("serve", cmd_serve, help="run the FastAPI service")
    x.add_argument("--host", default="0.0.0.0"); x.add_argument("--port", type=int, default=8000)  # noqa: E702
    x.add_argument("--workers", type=int, default=1)

    a = p.parse_args(argv)
    a.fn(a, s)