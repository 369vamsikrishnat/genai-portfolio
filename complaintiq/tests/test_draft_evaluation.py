import json
from types import SimpleNamespace

import pandas as pd

from complaintiq import cli
from complaintiq.embed import HashingEmbedder
from complaintiq.evals.draft import evaluate_grounded_drafts


def _artifact():
    meta = pd.DataFrame([
        (1, "2024-01-01", "A", "X", "alpha charge dispute", "Closed with explanation"),
        (2, "2024-01-02", "A", "X", "alpha charge was disputed", "Closed with non-monetary relief"),
        (3, "2024-01-03", "B", "Y", "beta mortgage foreclosure", "Closed with explanation"),
        (4, "2024-01-04", "A", "X", "alpha charge follow up", "Closed with explanation"),
        (5, "2024-01-05", "B", "Y", "beta foreclosure follow up", "Closed with explanation"),
        (6, "2024-01-06", "A", "X", "alpha charge dispute", "Closed with explanation"),
        (7, "2024-01-07", "A", "X", "alpha charge latest detail", "Closed with explanation"),
    ], columns=["complaint_id", "date_received", "product", "issue", "narrative", "company_response"])
    meta["date_received"] = pd.to_datetime(meta["date_received"])
    embedder = HashingEmbedder()
    return SimpleNamespace(
        manifest={"n_train": 3, "data_source": "processed", "data_source_type": "real_cfpb"},
        meta=meta,
        vectors=embedder.encode(meta["narrative"].tolist()),
        embedder=embedder,
    )


def test_evaluate_grounded_drafts_checks_citations_and_template():
    report = evaluate_grounded_drafts(_artifact(), n_queries=10, seed=2, min_dense_score=0.0)

    assert report["evaluation_type"] == "automated_evidence_grounding_checks"
    assert report["split"]["train_index_rows"] == 3
    assert report["split"]["boundary_date_rows_excluded"] == 0
    assert report["n_queries"] == 3
    assert report["model_generation_calls"] == 0
    assert report["checks"]["citation_coverage"] == 1.0
    assert report["checks"]["all_retrieved_precedents_cited"] == 1.0
    assert report["checks"]["evidence_template_validation_rate"] == 1.0
    assert report["checks"]["unsupported_factual_fields_detected"] == 0
    assert report["human_judged_quality"]["measured"] is False


def test_eval_drafts_cli_saves_reproducible_reports(monkeypatch, settings, capsys):
    art = _artifact()
    monkeypatch.setattr(cli.Settings, "from_env", classmethod(lambda cls: settings))
    monkeypatch.setattr(cli, "_art", lambda _settings: art)

    cli.main(["eval-drafts", "--n-queries", "2", "--seed", "7"])

    report = json.loads((settings.results_dir / "evidence_generation.json").read_text())
    markdown = (settings.results_dir / "evidence_generation.md").read_text()
    assert report["n_queries"] == 2
    assert report["seed"] == 7
    assert report["human_judged_quality"]["measured"] is False
    assert "not presented as correct, legally approved" in markdown
    assert "No human review study was run" in markdown
    assert markdown in capsys.readouterr().out
