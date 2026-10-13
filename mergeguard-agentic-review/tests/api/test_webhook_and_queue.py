from __future__ import annotations

import hashlib
import hmac
import json

from fastapi.testclient import TestClient

from mergeguard.api import app as api_app
from mergeguard.worker import main as worker


class FakeRedis:
    def __init__(self):
        self.jobs = {}
        self.queue = []
        self.processing = []
        self.dead_letter = []
        self.dedupe = {}
        self.expirations = {}

    def _list(self, key):
        return {
            api_app.QUEUE_KEY: self.queue,
            worker.PROCESSING_KEY: self.processing,
            worker.DEAD_LETTER_KEY: self.dead_letter,
        }[key]

    def hgetall(self, key):
        return dict(self.jobs.get(key, {}))

    def hset(self, key, *args, **kwargs):
        if "mapping" in kwargs:
            self.jobs.setdefault(key, {}).update(kwargs["mapping"])
        elif args:
            self.jobs.setdefault(key, {})[args[0]] = args[1]

    def expire(self, key, seconds):
        self.expirations[key] = seconds
        return True

    def hincrby(self, key, field, amount):
        value = int(self.jobs.setdefault(key, {}).get(field, 0)) + amount
        self.jobs[key][field] = str(value)
        return value

    def lpush(self, key, value):
        self._list(key).insert(0, value)

    def lmove(self, source, destination, src="LEFT", dest="RIGHT"):
        source_list = self._list(source)
        destination_list = self._list(destination)
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
        values = self._list(key)
        removed = 0
        while value in values and (count == 0 or removed < abs(count)):
            index = values.index(value) if count >= 0 else len(values) - 1 - values[::-1].index(value)
            values.pop(index)
            removed += 1
        return removed

    def eval(self, script, number_of_keys, *values):
        if number_of_keys == 3 and values[0].startswith(api_app.DEDUPE_PREFIX):
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
                "pr_number": str(pr_number),
                "head_sha": head_sha,
                "status": "queued",
                "attempts": "0",
                "result": "",
            }
            self.expire(job_key, int(ttl))
            self.lpush(queue_key, serialized_job)
            return job_id
        if number_of_keys == 3:
            processing_key, target_key, job_key, raw, *arguments = values
            self.lrem(processing_key, 1, raw)
            self.lpush(target_key, raw)
            status = "failed" if target_key == worker.DEAD_LETTER_KEY else "queued"
            updates = {"status": status}
            ttl = arguments[-1]
            if len(arguments) == 2:
                updates["attempts"] = str(arguments[0])
            self.hset(job_key, mapping=updates)
            self.expire(job_key, int(ttl))
            return 1
        job_key, queue_key, resume_payload = values
        if self.jobs.get(job_key, {}).get("status") != "awaiting_review":
            return 0
        self.jobs[job_key]["status"] = "review_queued"
        self.lpush(queue_key, resume_payload)
        return 1


def _signed_request(client, secret, payload, event="pull_request"):
    raw_body = json.dumps(payload, separators=(",", ":")).encode()
    signature = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return client.post(
        "/webhook/github",
        content=raw_body,
        headers={
            "X-Hub-Signature-256": f"sha256={signature}",
            "X-GitHub-Event": event,
            "Content-Type": "application/json",
        },
    )


def _github_payload(head_sha="head-sha-1", action="opened"):
    return {
        "action": action,
        "number": 17,
        "repository": {"name": "widget", "owner": {"login": "acme"}},
        "pull_request": {"number": 17, "head": {"sha": head_sha}},
    }


def test_signed_github_webhook_creates_one_deduplicated_job(monkeypatch):
    fake_redis = FakeRedis()
    monkeypatch.setattr(api_app, "redis_client", fake_redis)
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "webhook-secret")
    client = TestClient(api_app.app)

    first = _signed_request(client, "webhook-secret", _github_payload())
    second = _signed_request(client, "webhook-secret", _github_payload())

    assert first.status_code == 202
    assert second.status_code == 202
    assert first.json()["job_id"] == second.json()["job_id"]
    assert second.json()["deduplicated"] is True
    assert len(fake_redis.queue) == 1
    job_id = first.json()["job_id"]
    job = fake_redis.hgetall(api_app._job_key(job_id))
    assert job["head_sha"] == "head-sha-1"
    assert job["attempts"] == "0"
    assert fake_redis.expirations[api_app._job_key(job_id)] == api_app.JOB_TTL_SECONDS


def test_github_webhook_rejects_bad_signature_and_ignores_other_events(monkeypatch):
    fake_redis = FakeRedis()
    monkeypatch.setattr(api_app, "redis_client", fake_redis)
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "webhook-secret")
    client = TestClient(api_app.app)
    payload = _github_payload()
    raw_body = json.dumps(payload).encode()

    bad_signature = client.post(
        "/webhook/github",
        content=raw_body,
        headers={"X-Hub-Signature-256": "sha256=bad", "X-GitHub-Event": "pull_request"},
    )
    ignored_event = _signed_request(client, "webhook-secret", payload, event="issues")

    assert bad_signature.status_code == 401
    assert ignored_event.status_code == 204
    assert fake_redis.queue == []


def test_only_supported_pull_request_actions_are_enqueued(monkeypatch):
    fake_redis = FakeRedis()
    monkeypatch.setattr(api_app, "redis_client", fake_redis)
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "webhook-secret")
    response = _signed_request(TestClient(api_app.app), "webhook-secret", _github_payload(action="closed"))

    assert response.status_code == 204
    assert fake_redis.queue == []


def test_processing_items_are_recovered_and_success_is_acknowledged(monkeypatch):
    fake_redis = FakeRedis()
    job_id = "dcae68ad-714e-4d03-84a3-85a0ddb5cd67"
    raw = json.dumps({"job_id": job_id, "owner": "acme", "repo": "widget", "pr_number": 17})
    fake_redis.processing.append(raw)
    fake_redis.jobs[api_app._job_key(job_id)] = {"attempts": "1", "status": "running"}
    monkeypatch.setattr(worker, "redis_client", fake_redis)

    assert worker.recover_processing_jobs() == 1
    assert fake_redis.processing == []
    reserved = fake_redis.blmove(api_app.QUEUE_KEY, worker.PROCESSING_KEY, 0, src="RIGHT", dest="LEFT")
    monkeypatch.setattr(worker, "process_job", lambda payload, checkpointer: True)

    worker.process_queue_item(reserved, checkpointer=None)

    assert fake_redis.processing == []
    assert fake_redis.jobs[api_app._job_key(job_id)]["attempts"] == "2"
    assert fake_redis.expirations[api_app._job_key(job_id)] == worker.JOB_TTL_SECONDS


def test_third_failed_attempt_moves_job_to_dead_letter(monkeypatch):
    fake_redis = FakeRedis()
    job_id = "dcae68ad-714e-4d03-84a3-85a0ddb5cd67"
    raw = json.dumps({"job_id": job_id, "owner": "acme", "repo": "widget", "pr_number": 17})
    fake_redis.jobs[api_app._job_key(job_id)] = {"attempts": "0", "status": "queued"}
    fake_redis.queue.append(raw)
    monkeypatch.setattr(worker, "redis_client", fake_redis)
    monkeypatch.setattr(worker, "process_job", lambda payload, checkpointer: False)
    monkeypatch.setattr(worker, "_persist_finished_run", lambda *args, **kwargs: None)

    for _ in range(worker.MAX_JOB_ATTEMPTS):
        reserved = fake_redis.blmove(api_app.QUEUE_KEY, worker.PROCESSING_KEY, 0, src="RIGHT", dest="LEFT")
        worker.process_queue_item(reserved, checkpointer=None)

    job = fake_redis.hgetall(api_app._job_key(job_id))
    assert fake_redis.queue == []
    assert fake_redis.processing == []
    assert fake_redis.dead_letter == [raw]
    assert job["attempts"] == "3"
    assert job["status"] == "failed"


def test_startup_recovery_deadletters_exhausted_processing_job(monkeypatch):
    fake_redis = FakeRedis()
    job_id = "dcae68ad-714e-4d03-84a3-85a0ddb5cd67"
    raw = json.dumps({"job_id": job_id, "owner": "acme", "repo": "widget", "pr_number": 17})
    fake_redis.processing.append(raw)
    fake_redis.jobs[api_app._job_key(job_id)] = {"attempts": "3", "status": "running"}
    monkeypatch.setattr(worker, "redis_client", fake_redis)
    monkeypatch.setattr(worker, "_persist_finished_run", lambda *args, **kwargs: None)

    assert worker.recover_processing_jobs() == 0
    assert fake_redis.processing == []
    assert fake_redis.queue == []
    assert fake_redis.dead_letter == [raw]
    assert fake_redis.jobs[api_app._job_key(job_id)]["status"] == "failed"