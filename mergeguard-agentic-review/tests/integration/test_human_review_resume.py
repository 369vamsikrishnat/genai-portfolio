from __future__ import annotations

import json

from fastapi.testclient import TestClient
from langgraph.checkpoint.memory import MemorySaver

from mergeguard.storage import db
from mergeguard.workflow import graph
from mergeguard.api import app as api_app
from mergeguard.worker import main as worker
from mergeguard.workflow.graph import GRAPH_RECURSION_LIMIT, build_graph


class FakeRedis:
    def __init__(self):
        self.jobs = {}
        self.queue = []

    def hgetall(self, key):
        return dict(self.jobs.get(key, {}))

    def hset(self, key, *args, **kwargs):
        if "mapping" in kwargs:
            self.jobs.setdefault(key, {}).update(kwargs["mapping"])
        elif args:
            self.jobs.setdefault(key, {})[args[0]] = args[1]

    def eval(self, script, number_of_keys, job_key, queue_key, resume_payload):
        if self.jobs.get(job_key, {}).get("status") != "awaiting_review":
            return 0
        self.jobs[job_key]["status"] = "review_queued"
        self.queue.append(resume_payload)
        return 1


def _pending_graph_review(monkeypatch, job_id: str, checkpointer: MemorySaver):
    monkeypatch.setattr(graph, "code_analysis_node", lambda state: {"code_findings": [], "injection_flags": []})
    monkeypatch.setattr(graph, "test_execution_node", lambda state: {})
    monkeypatch.setattr(graph, "security_review_node", lambda state: {"security_findings": []})
    state = {
        "job_id": job_id,
        "owner": "acme",
        "repo": "app",
        "pr_number": 8,
        "head_sha": "abc123",
        "changed_files": ["src/app.py"],
        "test_results": [{"status": "failed", "summary": "assertion failed"}],
    }
    result = build_graph().compile(checkpointer=checkpointer).invoke(
        state,
        config={
            "configurable": {"thread_id": job_id},
            "recursion_limit": GRAPH_RECURSION_LIMIT,
        },
    )
    return result


def test_block_pauses_and_authenticated_override_resumes_with_memory_saver(monkeypatch):
    job_id = "dcae68ad-714e-4d03-84a3-85a0ddb5cd67"
    checkpointer = MemorySaver()
    result = _pending_graph_review(monkeypatch, job_id, checkpointer)
    review = result["__interrupt__"][0].value
    assert review["verdict"] == "BLOCK"

    fake_redis = FakeRedis()
    job_key = api_app._job_key(job_id)
    fake_redis.jobs[job_key] = {
        "job_id": job_id,
        "status": "awaiting_review",
        "review_payload": json.dumps(review),
    }
    monkeypatch.setattr(api_app, "redis_client", fake_redis)
    monkeypatch.setattr(worker, "redis_client", fake_redis)
    monkeypatch.setenv("WEBHOOK_API_KEY", "test-key")
    database_updates = []
    monkeypatch.setattr(db, "record_human_review", lambda **values: database_updates.append(values))
    monkeypatch.setattr(db, "finish_run", lambda **values: database_updates.append(values))

    client = TestClient(api_app.app)
    assert client.get(f"/pr/{job_id}/status").json()["review_payload"]["verdict"] == "BLOCK"
    assert fake_redis.queue == []
    assert client.post(
        f"/pr/{job_id}/review",
        json={"decision": "MERGE", "reason": "The destructive query is guarded and reviewed."},
    ).status_code == 401
    assert client.post(
        f"/pr/{job_id}/review",
        headers={"X-API-Key": "test-key"},
        json={"decision": "MERGE", "reason": "   "},
    ).status_code == 422

    response = client.post(
        f"/pr/{job_id}/review",
        headers={"X-API-Key": "test-key"},
        json={"decision": "MERGE", "reason": "The destructive query is guarded and reviewed."},
    )
    assert response.status_code == 202
    queued_payload = json.loads(fake_redis.queue[0])
    assert queued_payload["action"] == "resume"

    worker.resume_job(queued_payload, checkpointer)

    finished_job = fake_redis.hgetall(job_key)
    finished_result = json.loads(finished_job["result"])
    assert finished_job["status"] == "completed"
    assert finished_result["final_verdict"] == "MERGE"
    assert finished_result["human_override"] is True
    assert finished_result["override_reason"] == "The destructive query is guarded and reviewed."
    assert database_updates[0]["human_override"] is True
    assert database_updates[0]["override_reason"] == "The destructive query is guarded and reviewed."
    assert database_updates[1]["final_verdict"] == "MERGE"
    assert database_updates[1]["status"] == "completed"

    status = client.get(f"/pr/{job_id}/status").json()
    assert status["status"] == "completed"
    assert "review_payload" not in status
    assert client.post(
        f"/pr/{job_id}/review",
        headers={"X-API-Key": "test-key"},
        json={"decision": "MERGE", "reason": "duplicate"},
    ).status_code == 409


def test_review_endpoint_returns_409_when_job_is_not_awaiting_review(monkeypatch):
    job_id = "dcae68ad-714e-4d03-84a3-85a0ddb5cd67"
    fake_redis = FakeRedis()
    fake_redis.jobs[api_app._job_key(job_id)] = {"status": "running"}
    monkeypatch.setattr(api_app, "redis_client", fake_redis)
    monkeypatch.setenv("WEBHOOK_API_KEY", "test-key")

    response = TestClient(api_app.app).post(
        f"/pr/{job_id}/review",
        headers={"X-API-Key": "test-key"},
        json={"decision": "BLOCK", "reason": ""},
    )

    assert response.status_code == 409
    assert fake_redis.queue == []