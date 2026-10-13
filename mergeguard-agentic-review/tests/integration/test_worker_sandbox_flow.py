from __future__ import annotations

import json
from pathlib import Path

from mergeguard.storage import db
from mergeguard.workflow import graph
from mergeguard.sandbox import jobs as sandbox_jobs
from mergeguard.worker import main as worker
from mergeguard.agents import test_execution
from mergeguard.tools.sandbox_client import SandboxedTestRunner, TestResult


class FakeRedis:
    def __init__(self):
        self.updates = []

    def hset(self, key, *args, **kwargs):
        self.updates.append((key, args, kwargs))


def test_worker_stages_workspace_before_graph_sandbox_run_and_cleans_workspace(monkeypatch, tmp_path):
    redis_client = FakeRedis()
    staged = {}
    submitted = []
    persisted = {}
    tool_events = []

    class FakeGitHubClient:
        def get_pull_request(self, owner, repo, pr_number):
            return {"title": "Test change", "head": {"sha": "abc123"}}

        def get_changed_files(self, owner, repo, pr_number):
            return [{"filename": "src/app.py", "patch": "+value = 1"}]

        def get_pr_conversation(self, owner, repo, pr_number):
            return [{"body": "Please review the change."}]

        def get_source_archive(self, owner, repo, ref):
            assert ref == "abc123"
            return b"zip-archive"

    def fake_extract(archive, workspace):
        staged["archive"] = archive
        staged["workspace"] = workspace
        workspace.mkdir(parents=True)

    def fake_submit(job_id):
        assert (tmp_path / job_id).is_dir()
        submitted.append(job_id)
        return TestResult(status="passed", summary="PR tests passed.")

    def fake_record_tool_event(job_id, tool, fn):
        try:
            result = fn()
        except Exception as error:
            tool_events.append((job_id, tool, False, type(error).__name__))
            raise
        tool_events.append((job_id, tool, True, None))
        return result

    monkeypatch.setattr(worker, "redis_client", redis_client)
    monkeypatch.setattr(worker, "GitHubClient", FakeGitHubClient)
    monkeypatch.setattr(worker, "extract_source_archive", fake_extract)
    monkeypatch.setattr(sandbox_jobs, "submit_sandbox_job", fake_submit)
    monkeypatch.setattr(
        test_execution,
        "call_agent_tool",
        lambda agent, server, tool, arguments: SandboxedTestRunner()
        .run_tests(arguments["job_id"])
        .model_dump(),
    )
    monkeypatch.setattr(db, "create_run", lambda **kwargs: persisted.update(start=kwargs))
    monkeypatch.setattr(db, "finish_run", lambda **kwargs: persisted.update(finish=kwargs))
    monkeypatch.setattr(db, "record_tool_event", fake_record_tool_event)
    monkeypatch.setattr(graph, "code_analysis_node", lambda state: {"code_findings": [], "injection_flags": []})
    monkeypatch.setattr(
        graph,
        "security_review_node",
        lambda state: {"security_findings": [], "agents_skipped": ["security_review"]},
    )
    monkeypatch.setenv("SANDBOX_WORKSPACE_DIR", str(tmp_path))

    job_id = "dcae68ad-714e-4d03-84a3-85a0ddb5cd67"
    worker.process_job(
        {"job_id": job_id, "owner": "acme", "repo": "app", "pr_number": 7}
    )

    assert staged["archive"] == b"zip-archive"
    assert submitted == [job_id]
    stored = json.loads(redis_client.updates[-1][2]["mapping"]["result"])
    assert stored["test_results"][0]["status"] == "passed"
    assert stored["pr_title"] == "Test change"
    assert stored["changed_files"] == ["src/app.py"]
    assert stored["agents_skipped"] == ["security_review"]
    assert persisted["start"]["job_id"] == job_id
    assert persisted["finish"]["status"] == "completed"
    assert len(tool_events) >= 5
    assert not Path(staged["workspace"]).exists()
    assert redis_client.updates[-1][2]["mapping"]["status"] == "completed"