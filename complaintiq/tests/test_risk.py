import json
from types import SimpleNamespace

import pandas as pd
import pytest

from complaintiq import cli
from complaintiq.evals.risk import (
    audit_rule_coverage,
    coverage_to_markdown,
    score_rules,
    score_to_markdown,
)
from complaintiq.risk import risk_flags, risk_matches


def test_risk_matches_explain_flags_without_changing_flag_api():
    text = "Someone else opened an account in my name. I will pursue legal action."

    matches = risk_matches(text)

    assert matches["legal_threat"] == ["I will pursue legal action"]
    assert matches["identity_theft_fraud"] == ["Someone else opened an account"]
    assert risk_flags(text) == list(matches)
    assert risk_flags("my statement was late") == []


def test_potentially_unauthorized_transactions_trigger_fraud_review():
    text = (
        "I am concerned that transactions may have been processed "
        "without my authorization."
    )

    matches = risk_matches(text)

    assert "identity_theft_fraud" in matches
    assert any("without my authorization" in item for item in matches["identity_theft_fraud"])
    assert risk_flags("I noticed an unexpected balance adjustment.") == []


def test_score_rules_reports_overall_per_rule_and_severity_metrics(tmp_path):
    sheet = tmp_path / "labels.csv"
    pd.DataFrame([
        {"narrative": "I will pursue legal action if this is not resolved", "risk_flag": 1, "severity": "high"},
        {"narrative": "CFPB sent my account letter", "risk_flag": 0, "severity": "medium"},
        {"narrative": "routine billing question", "risk_flag": 0, "severity": "low"},
    ]).to_csv(sheet, index=False)

    report = score_rules(str(sheet))
    markdown = score_to_markdown(report)

    assert report["n_labelled"] == 3
    assert report["positives"] == 1
    assert report["precision"] == 1.0
    assert report["recall"] == 1.0
    assert report["accuracy"] == 1.0
    assert report["per_rule"]["legal_threat"] == {
        "support": 1, "precision": 1.0, "recall": 1.0, "f1": 1.0,
    }
    assert report["severity"]["high"]["rule_recall"] == 1.0
    assert report["severity"]["medium"]["rule_flagged"] == 0
    assert "Per-rule metrics" in markdown
    assert "Severity breakdown" in markdown


def test_score_rules_requires_labels(tmp_path):
    sheet = tmp_path / "labels.csv"
    pd.DataFrame([{"narrative": "text", "risk_flag": ""}]).to_csv(sheet, index=False)

    with pytest.raises(ValueError, match="no labelled rows"):
        score_rules(str(sheet))


def test_risk_coverage_audit_explicitly_does_not_claim_quality():
    df = pd.DataFrame({
        "narrative": ["I will pursue legal action if this is not resolved", "regular question", "CFPB fraud alert"],
        "product": ["Mortgage", "Mortgage", "Credit card"],
        "date_received": pd.to_datetime(["2025-01-01", "2025-01-02", "2025-01-03"]),
    })
    manifest = {
        "data_source": "processed",
        "data_source_type": "real_cfpb",
        "label_col": "product",
        "n_train": 2,
        "temporal_split": {"test_start": "2025-01-01"},
    }

    report = audit_rule_coverage(df, manifest)
    markdown = coverage_to_markdown(report)

    assert report["evaluation_type"] == "unlabeled_rule_coverage"
    assert report["n_test"] == 3
    assert report["flagged_rows"] == 1
    assert report["rows_by_rule"]["legal_threat"]["rows"] == 1
    assert report["by_product"]["Mortgage"]["flagged_rows"] == 1
    assert "does not measure precision" in report["evaluation_note"]
    assert "not an ordered or calibrated priority score" in markdown


def test_risk_audit_cli_saves_holdout_coverage(monkeypatch, settings, capsys):
    artifact = SimpleNamespace(
        manifest={
            "n_train": 1,
            "data_source": "processed",
            "data_source_type": "real_cfpb",
            "label_col": "product",
            "temporal_split": {"test_start": "2025-01-01"},
        },
        meta=pd.DataFrame({
            "narrative": ["train", "I will contact my attorney", "routine"],
            "product": ["A", "A", "B"],
            "date_received": pd.to_datetime(["2024-01-01", "2025-01-01", "2025-01-02"]),
        }),
    )
    monkeypatch.setattr(cli.Settings, "from_env", classmethod(lambda cls: settings))
    monkeypatch.setattr(cli, "_art", lambda _settings: artifact)

    cli.main(["risk-audit"])

    report = json.loads((settings.results_dir / "risk_coverage.json").read_text())
    markdown = (settings.results_dir / "risk_coverage.md").read_text()
    assert report["n_test"] == 2
    assert report["flagged_rows"] == 1
    assert "not an ordered or calibrated priority score" in markdown
    assert markdown in capsys.readouterr().out


def test_label_sample_can_use_only_artifact_holdout(monkeypatch, settings, tmp_path):
    artifact = SimpleNamespace(
        manifest={"n_train": 2},
        meta=pd.DataFrame({
            "complaint_id": [1, 2, 3, 4],
            "narrative": ["train 1", "train 2", "test 1", "test 2"],
        }),
    )
    monkeypatch.setattr(cli.Settings, "from_env", classmethod(lambda cls: settings))
    monkeypatch.setattr(cli, "_art", lambda _settings: artifact)
    out = tmp_path / "holdout.csv"

    cli.main(["label-sample", "--artifact-holdout", "--n", "10", "--out", str(out)])

    sheet = pd.read_csv(out)
    assert set(sheet["complaint_id"]) == {3, 4}


def test_eval_risk_cli_saves_markdown_report(monkeypatch, settings, tmp_path, capsys):
    sheet = tmp_path / "labels.csv"
    pd.DataFrame([
        {"narrative": "I will contact my attorney", "risk_flag": 1, "severity": "high"},
        {"narrative": "routine", "risk_flag": 0, "severity": "low"},
    ]).to_csv(sheet, index=False)
    monkeypatch.setattr(cli.Settings, "from_env", classmethod(lambda cls: settings))

    cli.main(["eval-risk", "--sheet", str(sheet)])

    report = json.loads((settings.results_dir / "risk_rules.json").read_text())
    markdown = (settings.results_dir / "risk_rules.md").read_text()
    assert report["n_labelled"] == 2
    assert report["per_rule"]["legal_threat"]["recall"] == 1.0
    assert "Hand-labeled risk-rule evaluation" in markdown
    assert markdown in capsys.readouterr().out
