import json
from types import SimpleNamespace

import numpy as np
import pandas as pd

from complaintiq import cli
from complaintiq.classifier_metrics import evaluate_classifier


class FixedClassifier:
    def __init__(self):
        self.rows_seen = 0

    def predict_with_conf(self, X):
        self.rows_seen = len(X)
        return (np.array(["A", "A", "B", "B"][:len(X)]),
                np.array([0.95, 0.75, 0.45, 0.6][:len(X)]))


def test_evaluate_classifier_reports_metrics_and_confidence_curve():
    classifier = FixedClassifier()
    report = evaluate_classifier(
        classifier,
        np.arange(4).reshape(-1, 1),
        np.array(["A", "B", "A", "B"]),
        min_support=2,
    )

    assert classifier.rows_seen == 4
    assert report["n_test"] == 4
    assert report["macro_f1"] == 0.5
    assert report["weighted_f1"] == 0.5
    assert report["accuracy"] == 0.5
    assert report["ece"] >= 0
    assert report["per_class"]["A"]["support"] == 2
    assert report["per_class"]["B"]["support"] == 2
    assert [row["threshold"] for row in report["confidence_curve"]] == [
        0.0, 0.5, 0.6, 0.7, 0.8, 0.9,
    ]


def test_eval_classifier_cli_uses_full_holdout_and_saves_reports(
    monkeypatch, settings, capsys,
):
    classifier = FixedClassifier()
    artifact = SimpleNamespace(
        manifest={
            "n": 6,
            "n_train": 2,
            "label_col": "product",
            "embedder_arg": "hashing",
            "data_source": "data/processed",
            "data_source_type": "real_cfpb",
            "sample": 6,
            "temporal_split": {
                "strategy": "chronological_80_20",
                "train_rows": 2,
                "test_rows": 4,
            },
        },
        vectors=np.zeros((6, 2)),
        meta=pd.DataFrame({"product": ["A", "B", "A", "B", "A", "B"]}),
        clf=classifier,
    )
    monkeypatch.setattr(cli.Settings, "from_env", classmethod(lambda cls: settings))
    monkeypatch.setattr(cli, "_art", lambda _settings: artifact)

    cli.main(["eval-classifier", "--min-support", "2"])

    report_path = settings.results_dir / "classifier_metrics.json"
    markdown_path = settings.results_dir / "classifier_metrics.md"
    report = json.loads(report_path.read_text())
    markdown = markdown_path.read_text()

    assert classifier.rows_seen == 4
    assert report["n_test"] == 4
    assert report["data_source"] == "data/processed"
    assert report["data_source_type"] == "real_cfpb"
    assert report["sampled_rows"] == 6
    assert report["artifact_rows"] == 6
    assert report["label_col"] == "product"
    assert report["macro_f1"] == 0.5
    assert "Expected calibration error" in markdown
    assert "Per-class results" in markdown
    assert "data/processed" in markdown
    assert "real_cfpb" in markdown
    assert markdown in capsys.readouterr().out
