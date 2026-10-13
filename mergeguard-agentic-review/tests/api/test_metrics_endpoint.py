from __future__ import annotations

from fastapi.testclient import TestClient

from mergeguard.api import app as api_app
from mergeguard.observability.metrics import build_metrics


def test_empty_database_metrics_are_null_for_zero_denominators(monkeypatch):
    monkeypatch.setattr(
        api_app.db,
        "get_metrics_data",
        lambda: {"tool_events": [], "runs": []},
    )

    response = TestClient(api_app.app).get("/metrics")
    metrics = response.json()

    assert response.status_code == 200
    assert metrics["tool_success_rate"] is None
    assert metrics["task_completion_rate"] is None
    assert metrics["human_override_rate"] is None
    assert metrics["agents_skipped_pct"] is None
    assert metrics["jobs_by_status"] == {}
    assert metrics["total_runs"] == 0


def test_seeded_database_rows_produce_exact_metric_percentages(monkeypatch):
    monkeypatch.setattr(
        api_app.db,
        "get_metrics_data",
        lambda: {
            "tool_events": [
                {"success": True},
                {"success": True},
                {"success": False},
            ],
            "runs": [
                {
                    "status": "completed",
                    "human_override": True,
                    "review_status": "human_reviewed",
                    "agents_skipped": ["security_review"],
                },
                {
                    "status": "completed",
                    "human_override": False,
                    "review_status": "human_reviewed",
                    "agents_skipped": [],
                },
                {
                    "status": "failed",
                    "human_override": False,
                    "review_status": "auto_approved",
                    "agents_skipped": [],
                },
            ],
        },
    )

    metrics = TestClient(api_app.app).get("/metrics").json()

    assert metrics["tool_success_rate"] == 66.67
    assert metrics["task_completion_rate"] == 66.67
    assert metrics["human_override_rate"] == 50.0
    assert metrics["agents_skipped_pct"] == 11.11
    assert metrics["jobs_by_status"] == {"completed": 2, "failed": 1}
    assert metrics["total_runs"] == 3


def test_pure_metrics_return_null_when_run_denominators_are_empty():
    metrics = build_metrics(tool_events=[], runs=[])

    assert metrics["tool_success_rate"] is None
    assert metrics["task_completion_rate"] is None
    assert metrics["human_override_rate"] is None
    assert metrics["agents_skipped_pct"] is None