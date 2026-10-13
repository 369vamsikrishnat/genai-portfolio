from __future__ import annotations

import json
from pathlib import Path

from mergeguard.storage import db
from mergeguard.worker import main as worker
from mergeguard.workflow.graph import RiskFinding, SecurityFinding
from mergeguard.tools.sandbox_client import TestResult


class FakeRedis:
    def __init__(self):
        self.updates = []

    def hset(self, key, *args, **kwargs):
        self.updates.append((key, args, kwargs))


class FakeGraph:
    def compile(self, checkpointer=None):
        return self

    def invoke(self, state, config=None):
        return {
            **state,
            "code_findings": [
                RiskFinding(
                    severity="high",
                    description="Potential data loss.",
                    line_reference="app.py:12",
                )
            ],
            "security_findings": [
                SecurityFinding(
                    severity="high",
                    description="Review dependency risk.",
                    package_name="requests",
                )
            ],
        }


def test_worker_serializes_pydantic_findings_as_json_objects(monkeypatch, tmp_path: Path):
    redis_client = FakeRedis()
    database = {}

    class FakeGitHubClient:
        def get_pull_request(self, owner, repo, pr_number):
            return {"title": "Test change", "head": {"sha": "abc123"}}

        def get_changed_files(self, owner, repo, pr_number):
            return [{"filename": "app.py", "patch": "+value = 1"}]

        def get_pr_conversation(self, owner, repo, pr_number):
            return []

        def get_source_archive(self, owner, repo, ref):
            return b"zip-archive"

    def fake_extract(archive, workspace):
        workspace.mkdir(parents=True)

    def fake_record_tool_event(job_id, tool, fn):
        return fn()

    monkeypatch.setattr(worker, "redis_client", redis_client)
    monkeypatch.setattr(db, "create_run", lambda **kwargs: database.update(start=kwargs))
    monkeypatch.setattr(db, "finish_run", lambda **kwargs: database.update(finish=kwargs))
    monkeypatch.setattr(db, "record_tool_event", fake_record_tool_event)
    monkeypatch.setattr(worker, "GitHubClient", FakeGitHubClient)
    monkeypatch.setattr(worker, "extract_source_archive", fake_extract)
    monkeypatch.setattr(worker, "build_graph", FakeGraph)
    monkeypatch.setenv("SANDBOX_WORKSPACE_DIR", str(tmp_path))

    job_id = "dcae68ad-714e-4d03-84a3-85a0ddb5cd67"
    worker.process_job({"job_id": job_id, "owner": "acme", "repo": "app", "pr_number": 7})

    stored_mapping = redis_client.updates[-1][2]["mapping"]
    assert stored_mapping["status"] == "completed"
    stored_result = json.loads(stored_mapping["result"])

    assert isinstance(stored_result["code_findings"], list)
    assert isinstance(stored_result["code_findings"][0], dict)
    assert stored_result["code_findings"][0] == {
        "severity": "high",
        "description": "Potential data loss.",
        "line_reference": "app.py:12",
    }
    assert isinstance(stored_result["security_findings"][0], dict)
    assert stored_result["security_findings"][0]["package_name"] == "requests"