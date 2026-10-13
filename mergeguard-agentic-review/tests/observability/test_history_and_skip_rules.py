from mergeguard.observability import tracing
from mergeguard.observability.tracing import RecordEntry, RunHistory, build_history_entry, should_skip_security_review


def test_build_history_entry_tracks_verdict_and_cost_signal():
    entry = build_history_entry(
        owner="acme",
        repo="app",
        pr_number=21,
        verdict="MERGE",
        cost_saved=0.25,
    )

    assert entry["owner"] == "acme"
    assert entry["verdict"] == "MERGE"
    assert entry["cost_saved"] == 0.25


def test_run_history_stores_entries(monkeypatch):
    rows = []

    def create_run(**kwargs):
        rows.append({**kwargs, "status": "running"})

    def finish_run(**kwargs):
        rows[-1].update(kwargs)

    monkeypatch.setattr(tracing.db, "create_run", create_run)
    monkeypatch.setattr(tracing.db, "finish_run", finish_run)
    monkeypatch.setattr(tracing.db, "get_run_history", lambda limit=None: rows[-limit:] if limit else rows)

    history = RunHistory()
    entry = history.add(
        owner="acme",
        repo="app",
        pr_number=21,
        verdict="BLOCK",
        human_override=False,
        reasoning="suspicious dependency change",
    )

    assert entry["verdict"] == "BLOCK"
    assert history.latest()["verdict"] == "BLOCK"


def test_should_skip_security_review_when_no_dependency_files_changed():
    assert should_skip_security_review(["src/app.py", "tests/test_app.py"]) is True
    assert should_skip_security_review(["requirements.txt", "src/app.py"]) is False
