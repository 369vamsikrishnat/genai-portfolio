from __future__ import annotations

import json

from fastapi.testclient import TestClient

from mergeguard.api import app as api_app


class FakePipeline:
    def __init__(self, client):
        self.client = client
        self.commands = []

    def hset(self, key, mapping):
        self.commands.append(("hset", key, mapping))
        return self

    def lpush(self, key, value):
        self.commands.append(("lpush", key, value))
        return self

    def execute(self):
        for command, key, value in self.commands:
            if command == "hset":
                self.client.jobs[key] = value
            else:
                self.client.queue.append(value)


class FakeRedis:
    def __init__(self):
        self.jobs = {}
        self.queue = []
        self.dedupe = {}
        self.expirations = {}
        self.processing = []
        self.dead_letter = []

    def ping(self):
        return True

    def scan_iter(self, pattern):
        return iter(self.jobs)

    def hgetall(self, key):
        return dict(self.jobs.get(key, {}))

    def hset(self, key, *args, **kwargs):
        if "mapping" in kwargs:
            self.jobs.setdefault(key, {}).update(kwargs["mapping"])
        elif args:
            self.jobs.setdefault(key, {})[args[0]] = args[1]

    def eval(self, script, number_of_keys, *values):
        if number_of_keys == 3:
            dedupe_key, job_key, queue_key, job_id, owner, repo, pr_number, head_sha, ttl, serialized_job = values
            existing = self.dedupe.get(dedupe_key)
            if existing:
                status = self.jobs.get(f"mergeguard:job:{existing}", {}).get("status")
                if status in {"queued", "running", "awaiting_review", "review_queued", "resuming"}:
                    return existing
            self.dedupe[dedupe_key] = job_id
            self.jobs[job_key] = {
                "job_id": job_id,
                "owner": owner,
                "repo": repo,
                "pr_number": pr_number,
                "head_sha": head_sha,
                "status": "queued",
                "attempts": "0",
                "result": "",
            }
            self.expirations[job_key] = int(ttl)
            self.queue.insert(0, serialized_job)
            return job_id
        job_key, queue_key, serialized_job = values
        if self.jobs.get(job_key, {}).get("status") != "awaiting_review":
            return 0
        self.jobs[job_key]["status"] = "review_queued"
        self.queue.insert(0, serialized_job)
        return 1

    def expire(self, key, seconds):
        self.expirations[key] = seconds
        return True

    def hincrby(self, key, field, amount):
        value = int(self.jobs.setdefault(key, {}).get(field, 0)) + amount
        self.jobs[key][field] = str(value)
        return value

    def lmove(self, source, destination, src="LEFT", dest="RIGHT"):
        source_list = self._list_for(source)
        destination_list = self._list_for(destination)
        if not source_list:
            return None
        value = source_list.pop(0 if src == "LEFT" else -1)
        destination_list.insert(0 if dest == "LEFT" else len(destination_list), value)
        return value

    def lindex(self, key, index):
        values = self._list(key)
        if not values:
            return None
        return values[index]

    def blmove(self, source, destination, timeout, src="LEFT", dest="RIGHT"):
        return self.lmove(source, destination, src, dest)

    def lrem(self, key, count, value):
        values = self._list_for(key)
        removed = 0
        while value in values and (count == 0 or removed < abs(count)):
            index = values.index(value) if count >= 0 else len(values) - 1 - values[::-1].index(value)
            values.pop(index)
            removed += 1
        return removed

    def lpush(self, key, value):
        self._list_for(key).insert(0, value)

    def _list_for(self, key):
        if key == "mergeguard:processing":
            return self.processing
        if key == "mergeguard:dead_letter":
            return self.dead_letter
        return self.queue


def test_runtime_health_metrics_and_authenticated_webhook(monkeypatch):
    fake_redis = FakeRedis()
    monkeypatch.setattr(api_app, "redis_client", fake_redis)
    monkeypatch.setattr(api_app.db, "get_metrics_data", lambda: {"tool_events": [], "runs": []})
    monkeypatch.setattr(
        api_app,
        "GitHubClient",
        lambda: type("FakeGitHub", (), {"get_pull_request": lambda self, owner, repo, number: {"head": {"sha": "head-1"}}})(),
    )
    monkeypatch.setenv("WEBHOOK_API_KEY", "test-key")
    client = TestClient(api_app.app)

    assert client.get("/health").status_code == 200
    assert client.get("/metrics").json()["jobs_by_status"] == {}
    assert client.post(
        "/webhook/pr",
        json={"owner": "acme", "repo": "app", "pr_number": 42},
    ).status_code == 401

    response = client.post(
        "/webhook/pr",
        headers={"X-API-Key": "test-key"},
        json={"owner": "acme", "repo": "app", "pr_number": 42},
    )
    assert response.status_code == 202
    job_id = response.json()["job_id"]
    assert json.loads(fake_redis.queue[0])["job_id"] == job_id
    assert client.get(f"/pr/{job_id}/status").json()["status"] == "queued"
    assert client.get("/pr/missing/status").status_code == 404
