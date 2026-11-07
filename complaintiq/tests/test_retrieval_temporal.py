import json
from types import SimpleNamespace

import pandas as pd

from complaintiq import cli
from complaintiq.embed import HashingEmbedder
from complaintiq.evals.retrieval import run_temporal_evaluation


def _temporal_artifact():
    meta = pd.DataFrame([
        (1, "2024-01-01", "A", "X", "apple alpha complaint"),
        (2, "2024-01-02", "A", "X", "apple alpha second complaint"),
        (3, "2024-01-02", "B", "Y", "banana beta complaint"),
        (4, "2024-01-02", "B", "Y", "banana beta another case"),
        (5, "2024-01-02", "A", "X", "boundary date is excluded"),
        (6, "2024-01-03", "A", "X", "apple alpha later query"),
        (7, "2024-01-03", "B", "Y", "banana beta later query"),
        (8, "2024-01-03", "C", "Z", "category absent from training"),
        (9, "2024-01-04", "A", "X", "apple alpha complaint"),
        (10, "2024-01-04", "A", "X", "apple alpha later query"),
        (11, "2024-01-04", "B", "Y", "banana beta final query"),
    ], columns=["complaint_id", "date_received", "product", "issue", "narrative"])
    meta["date_received"] = pd.to_datetime(meta["date_received"])
    embedder = HashingEmbedder()
    vectors = embedder.encode(meta["narrative"].tolist())
    return SimpleNamespace(
        manifest={"n_train": 4, "embedder_arg": "hashing"},
        meta=meta,
        vectors=vectors,
        embedder=embedder,
    )


def test_temporal_eval_excludes_boundary_duplicates_and_test_documents():
    report = run_temporal_evaluation(_temporal_artifact(), n_queries=20, seed=4)

    assert report["evaluation_type"] == "temporal_holdout_with_weak_labels"
    assert report["relevance"]["type"] == "proxy"
    assert "not a semantic embedding model" in report["embedder_note"]
    assert report["n_retrieval_docs"] == 4
    assert report["split"]["duplicate_train_templates_removed"] == 0
    assert report["split"]["same_boundary_date_excluded"] == 1
    assert report["split"]["cross_split_template_queries_excluded"] == 1
    assert report["split"]["duplicate_test_template_queries_excluded"] == 1
    assert report["split"]["queries_without_train_relevance_group_excluded"] == 1
    assert report["split"]["cross_split_template_hashes_before_exclusion"] == 1
    assert report["n_queries"] == 3
    assert set(report["query_ids"]).isdisjoint({1, 2, 3, 4})
    assert set(report["modes"]) == {"bm25", "dense", "rrf"}
    for metrics in report["modes"].values():
        assert {"hit@1", "hit@5", "hit@10", "p@5", "p@10", "mrr@10",
                "ndcg@5", "ndcg@10", "search_latency_ms", "end_to_end_latency_ms"} <= set(metrics)
        assert metrics["search_latency_ms"]["p50"] > 0


def test_temporal_eval_is_deterministic_for_query_selection():
    art = _temporal_artifact()
    first = run_temporal_evaluation(art, n_queries=2, seed=13)
    second = run_temporal_evaluation(art, n_queries=2, seed=13)

    assert first["query_ids"] == second["query_ids"]
    assert first["query_ids_sha256"] == second["query_ids_sha256"]


def test_eval_retrieval_cli_saves_temporal_report(monkeypatch, settings, capsys):
    art = _temporal_artifact()
    monkeypatch.setattr(cli.Settings, "from_env", classmethod(lambda cls: settings))
    monkeypatch.setattr(cli, "_art", lambda _settings: art)

    cli.main(["eval-retrieval", "--n-queries", "2", "--seed", "5"])

    report = json.loads((settings.results_dir / "retrieval_evaluation.json").read_text())
    markdown = (settings.results_dir / "retrieval_evaluation.md").read_text()
    assert report["n_queries"] == 2
    assert report["seed"] == 5
    assert report["relevance"]["type"] == "proxy"
    assert "not human judgment" in markdown
    assert "not a semantic embedding model" in markdown
    assert "| P@1 |" in markdown
    assert (settings.results_dir / "retrieval_ablation.json").is_file()
    assert (settings.docs_dir / "ablation.md").is_file()
    assert markdown in capsys.readouterr().out
