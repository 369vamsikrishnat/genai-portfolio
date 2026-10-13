from mergeguard.observability.tracing import (
    RunHistory,
    calculate_run_metrics,
    describe_agent_decision,
)
from mergeguard.observability import tracing


def test_describe_agent_decision_returns_specific_trace_summary():
    summary = describe_agent_decision(
        agent="security_review",
        status="skipped",
        reason="No dependency files changed; skipping the security review saved time and reduced cost.",
    )

    assert summary["agent"] == "security_review"
    assert summary["status"] == "skipped"
    assert "dependency" in summary["reason"].lower()
    assert "cost" in summary["reason"].lower()


def test_calculate_run_metrics_tracks_agent_skip_pct_and_cost_saved():
    run_records = [
        {"agents_skipped": ["security_review"], "cost_saved": 0.20},
        {"agents_skipped": [], "cost_saved": 0.00},
        {"agents_skipped": ["security_review", "test_execution"], "cost_saved": 0.35},
    ]

    metrics = calculate_run_metrics(run_records)

    assert metrics["agents_skipped_pct"] == 33.33
    assert metrics["cost_saved_total"] == 0.55


def test_run_history_can_store_and_explain_an_agent_decision(monkeypatch):
    rows = []

    def create_run(**kwargs):
        rows.append({**kwargs, "status": "running"})

    def finish_run(**kwargs):
        rows[-1].update(kwargs)

    monkeypatch.setattr(tracing.db, "create_run", create_run)
    monkeypatch.setattr(tracing.db, "finish_run", finish_run)
    monkeypatch.setattr(tracing.db, "get_run_history", lambda limit=None: rows[-limit:] if limit else rows)

    history = RunHistory()
    history.add(
        owner="acme",
        repo="app",
        pr_number=101,
        verdict="MERGE",
        reasoning="Security skipped because no dependency files changed for this PR.",
        agent_decisions={
            "security_review": {"status": "skipped", "reason": "No dependency files changed."},
            "test_execution": {"status": "ran", "reason": "Core logic changed; tests were still required."},
        },
    )

    latest = history.latest()
    assert latest["agent_decisions"]["security_review"]["status"] == "skipped"
    assert latest["agent_decisions"]["test_execution"]["status"] == "ran"
