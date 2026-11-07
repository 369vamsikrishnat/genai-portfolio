import json
from pathlib import Path

import pandas as pd

from complaintiq import cli, spikes


def _counts():
    weeks = pd.date_range("2025-01-06", periods=9, freq="W-MON")
    return pd.DataFrame({
        "company": ["A"] * 9,
        "product": ["Cards"] * 9,
        "issue": ["Fraud"] * 9,
        "week": weeks,
        "n": [3] * 8 + [25],
    })


def test_eval_spikes_cli_saves_reproducible_reports(monkeypatch, settings, capsys):
    monkeypatch.setattr(cli.Settings, "from_env", classmethod(lambda cls: settings))
    monkeypatch.setattr(spikes, "load_weekly_counts", lambda *_args, **_kwargs: _counts())

    cli.main(["eval-spikes", "--src", "real-data", "--baseline-weeks", "8"])

    report = json.loads((settings.results_dir / "spike_evaluation.json").read_text())
    markdown = (settings.results_dir / "spike_evaluation.md").read_text()
    assert report["data"]["source"] == str(Path("real-data").resolve())
    assert report["data"]["source_type"] == "source_file"
    assert report["data"]["row_filter"] == "non-null date_received and non-null grouping keys"
    assert report["alert_summary"]["alerts"] == 1
    assert report["alert_summary"]["false_alert_count"] is None
    assert "not measurable" in markdown.lower()
    assert markdown in capsys.readouterr().out
