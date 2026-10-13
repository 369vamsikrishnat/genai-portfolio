from __future__ import annotations

import json

import pytest

from mergeguard.storage import db


class FakeCursor:
    def __init__(self, database):
        self.database = database
        self.description = []

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception, traceback):
        return False

    def execute(self, query, parameters=None):
        self.database.statements.append((query, parameters))


class FakeConnection:
    def __init__(self, database):
        self.database = database

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception, traceback):
        return False

    def cursor(self):
        return FakeCursor(self.database)


class FakeDatabase:
    def __init__(self):
        self.statements = []

    def connect(self):
        return FakeConnection(self)


def test_init_db_creates_runs_and_tool_events_tables(monkeypatch):
    fake_database = FakeDatabase()
    monkeypatch.setattr(db, "_connect", fake_database.connect)

    db.init_db()

    sql = "\n".join(statement for statement, _ in fake_database.statements)
    assert "CREATE TABLE IF NOT EXISTS runs" in sql
    assert "job_id uuid PRIMARY KEY" in sql
    assert "findings jsonb" in sql
    assert "cost_saved_usd numeric" in sql
    assert "CREATE TABLE IF NOT EXISTS tool_events" in sql
    assert "latency_ms integer" in sql


def test_run_lifecycle_stores_structured_payload_and_null_cost(monkeypatch):
    fake_database = FakeDatabase()
    monkeypatch.setattr(db, "_connect", fake_database.connect)

    db.create_run(job_id="123e4567-e89b-12d3-a456-426614174000", owner="acme", repo="app", pr_number=9)
    db.finish_run(
        job_id="123e4567-e89b-12d3-a456-426614174000",
        status="completed",
        head_sha="abc123",
        verdict="MERGE_WITH_COMMENTS",
        confidence=0.8,
        final_verdict="MERGE_WITH_COMMENTS",
        agents_skipped=["security_review"],
        reasons=["tests passed"],
        findings={"code_findings": [{"severity": "low", "description": "review", "line_reference": "unknown"}]},
        cost_saved_usd=None,
    )

    insert_sql, insert_parameters = fake_database.statements[0]
    update_sql, update_parameters = fake_database.statements[1]
    assert "INSERT INTO runs" in insert_sql
    assert insert_parameters == ("123e4567-e89b-12d3-a456-426614174000", "acme", "app", 9)
    assert "UPDATE runs SET" in update_sql
    assert update_parameters[0] == "abc123"
    assert update_parameters[7] == "completed"
    assert update_parameters[8] == ["security_review"]
    assert json.loads(update_parameters[9]) == ["tests passed"]
    assert json.loads(update_parameters[10])["code_findings"][0]["severity"] == "low"
    assert update_parameters[11] is None


def test_record_tool_event_captures_success_and_failure_without_masking(monkeypatch):
    events = []
    monkeypatch.setattr(db, "_insert_tool_event", lambda **event: events.append(event))

    assert db.record_tool_event("job-1", "github.get_pull_request", lambda: {"number": 9}) == {"number": 9}

    def failing_call():
        raise ValueError("sensitive raw error details")

    with pytest.raises(ValueError, match="sensitive raw error details"):
        db.record_tool_event("job-1", "gemini.code_analysis", failing_call)

    assert events[0]["success"] is True
    assert events[0]["error"] is None
    assert events[0]["latency_ms"] >= 0
    assert events[1]["success"] is False
    assert events[1]["error"] == "ValueError"
    assert events[1]["latency_ms"] >= 0


def test_record_human_review_updates_override_fields(monkeypatch):
    fake_database = FakeDatabase()
    monkeypatch.setattr(db, "_connect", fake_database.connect)

    db.record_human_review(
        job_id="123e4567-e89b-12d3-a456-426614174000",
        decision="MERGE",
        human_override=True,
        override_reason="Reviewed the evidence.",
    )

    query, parameters = fake_database.statements[0]
    assert "final_verdict = %s" in query
    assert "human_override = %s" in query
    assert "override_reason = %s" in query
    assert parameters == (
        "MERGE",
        True,
        "Reviewed the evidence.",
        "123e4567-e89b-12d3-a456-426614174000",
    )