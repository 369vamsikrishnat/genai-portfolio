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

    print(json.dumps(ingest(a.src, a.out, since_year=a.since, keep_without_narrative=a.keep_blank), indent=2))


def cmd_build(a, s):
    from .pipeline import build

    m = build(a.src, a.out or s.artifacts_dir, sample=a.sample, since_year=a.since,
              embedder_name=a.embedder or s.embedder, max_chars=s.max_chars)
    print(json.dumps(m, indent=2))


def cmd_ensure(a, s):
    from .pipeline import Artifacts, build
    from .synth import generate

    if Artifacts.exists(s.artifacts_dir):
        return print("artifacts present")
    p = s.data_dir / "synth.csv"
    p.parent.mkdir(parents=True, exist_ok=True)
    generate(a.n).to_csv(p, index=False)
    print(json.dumps(build(p, s.artifacts_dir, embedder_name="hashing"), indent=2))


def cmd_eval_retrieval(a, s):
    from .evals.retrieval import run_ablation, save, to_markdown
    from .retrieve import HybridRetriever, get_reranker

    art = _art(s)
    ret = HybridRetriever(art.texts, art.vectors, art.embedder, art.bm25, get_reranker(s.reranker))
    res = run_ablation(ret, art.meta, n_queries=a.n_queries)
    meta = {"embedder": art.manifest["embedder_arg"], "reranker": s.reranker}
    save(res, s.results_dir, s.docs_dir, meta)
    print(to_markdown(res, meta))


def cmd_eval_cascade(a, s):
    from .classify import cost_table_markdown, evaluate_cascade, run_llm_labels
    from .llm import get_llm

    art = _art(s)
    n_train = art.manifest["n_train"]
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
    llm = get_llm(s, truth)
    labels = [str(c) for c in art.clf.classes_]
    run = run_llm_labels(llm, texts, labels, s.price_in_per_m, s.price_out_per_m)
    rows = evaluate_cascade(y, pred, conf, run, a.thresholds, clf_ms)
    meta = {"n": len(pick), "llm": llm.name, "price_in": s.price_in_per_m, "price_out": s.price_out_per_m,
            "simulated": simulated}
    md = cost_table_markdown(rows, meta)
    s.results_dir.mkdir(parents=True, exist_ok=True)
    s.docs_dir.mkdir(parents=True, exist_ok=True)
    (s.results_dir / "cascade.json").write_text(json.dumps({"rows": rows, "meta": meta}, indent=2))
    (s.docs_dir / "cost_table.md").write_text("# Cascade cost table\n\n" + md)
    print(md)


def cmd_spikes(a, s):
    from .llm import get_llm
    from .spikes import detect_spikes, write_brief

    art = _art(s)
    sp = detect_spikes(art.meta, z_thresh=a.z, min_count=a.min_count)
    llm = get_llm(s) if a.brief else None
    out = []
    for _, r in sp.head(a.top).iterrows():
        d = r.to_dict()
        week = d["week"]
        m = art.meta
        ex = m[(m.company == d["company"]) & (m.issue == d["issue"]) & (m.date_received >= week)
               & (m.date_received < week + np.timedelta64(7, "D"))]["narrative"].head(5).tolist()
        d["brief"] = write_brief(d, ex, llm)
        d["week"] = f"{week:%Y-%m-%d}"
        out.append(d)
    s.results_dir.mkdir(parents=True, exist_ok=True)
    (s.results_dir / "spikes.json").write_text(json.dumps(out, indent=2, default=str))
    print(f"{len(sp)} spikes flagged; top {len(out)} saved to results/spikes.json")
    for d in out:
        print("-", d["brief"])


def cmd_scale(a, s):
    from .evals.scale import run_ladder, save, to_markdown

    vecs = None
    if not a.synthetic:
        vecs = _art(s).vectors
    res = run_ladder(vecs, a.sizes, n_queries=a.n_queries)
    save(res, s.results_dir, s.docs_dir)
    print(to_markdown(res))


def cmd_label_sample(a, s):
    from .data import load_complaints
    from .evals.risk import make_label_sheet

    df = load_complaints(a.src, since_year=a.since, only_narrative=True)
    make_label_sheet(df, a.out, n=a.n)
    print(f"wrote {a.out}: fill the risk_flag (0/1) and severity columns by hand, then run eval-risk")


def cmd_eval_risk(a, s):
    from .evals.risk import score_rules

    res = score_rules(a.sheet)
    s.results_dir.mkdir(parents=True, exist_ok=True)
    (s.results_dir / "risk_rules.json").write_text(json.dumps(res, indent=2))
    print(json.dumps(res, indent=2))


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
    from .service import Service

    cmd_ensure(argparse.Namespace(n=20000), s)
    svc = Service.from_artifacts(s)
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
    x = add("build", cmd_build, help="embed + train + index -> artifacts/")
    x.add_argument("--src", default="data/parquet"); x.add_argument("--out", default=None)  # noqa: E702
    x.add_argument("--sample", type=int, default=100_000); x.add_argument("--since", type=int, default=None)  # noqa: E702
    x.add_argument("--embedder", default=None)
    x = add("ensure-artifacts", cmd_ensure, help="build a synthetic demo if no artifacts exist")
    x.add_argument("--n", type=int, default=20000)
    x = add("eval-retrieval", cmd_eval_retrieval, help="BM25/dense/RRF/rerank ablation")
    x.add_argument("--n-queries", type=int, default=500)
    x = add("eval-cascade", cmd_eval_cascade, help="classifier vs LLM vs cascade cost table")
    x.add_argument("--n", type=int, default=300)
    x.add_argument("--thresholds", type=float, nargs="+", default=[0.5, 0.6, 0.7, 0.8, 0.9])
    x = add("spikes", cmd_spikes, help="weekly spike detection + briefs")
    x.add_argument("--z", type=float, default=3.0); x.add_argument("--min-count", type=int, default=10)  # noqa: E702
    x.add_argument("--top", type=int, default=10); x.add_argument("--brief", action="store_true")  # noqa: E702
    x = add("scale", cmd_scale, help="size ladder: quantisation recall/memory/latency")
    x.add_argument("--sizes", type=int, nargs="+", default=[100_000, 1_000_000])
    x.add_argument("--n-queries", type=int, default=200); x.add_argument("--synthetic", action="store_true")  # noqa: E702
    x = add("label-sample", cmd_label_sample, help="export a sheet to hand-label risk flags")
    x.add_argument("--src", default="data/parquet"); x.add_argument("--out", default="evals_labels.csv")  # noqa: E702
    x.add_argument("--n", type=int, default=250); x.add_argument("--since", type=int, default=None)  # noqa: E702
    x = add("eval-risk", cmd_eval_risk, help="score risk rules against your hand labels")
    x.add_argument("--sheet", default="evals_labels.csv")
    add("replay", cmd_replay, help="replay months as batches, print throughput")
    add("demo", cmd_demo, help="synthetic end-to-end demo")
    x = add("serve", cmd_serve, help="run the FastAPI service")
    x.add_argument("--host", default="0.0.0.0"); x.add_argument("--port", type=int, default=8000)  # noqa: E702
    x.add_argument("--workers", type=int, default=1)

    a = p.parse_args(argv)
    a.fn(a, s)
