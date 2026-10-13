from __future__ import annotations

import hmac
import hashlib
import json
import logging
import os
import uuid
from typing import Any
from typing import Literal

import redis
from fastapi import FastAPI, Header, HTTPException, Request, Response
from pydantic import BaseModel, Field

from mergeguard.storage import db
from mergeguard.observability.metrics import build_metrics
from mergeguard.tools.github_client import GitHubClient


REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
QUEUE_KEY = "mergeguard:review_jobs"
JOB_PREFIX = "mergeguard:job:"
DEDUPE_PREFIX = "mergeguard:dedupe:"
JOB_TTL_SECONDS = 7 * 24 * 60 * 60
redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
app = FastAPI(title="MergeGuard API", version="0.8.0")
logger = logging.getLogger(__name__)


class PullRequestWebhook(BaseModel):
    owner: str = Field(min_length=1)
    repo: str = Field(min_length=1)
    pr_number: int = Field(ge=1)
    head_sha: str | None = None


class HumanReviewRequest(BaseModel):
    decision: Literal["MERGE", "MERGE_WITH_COMMENTS", "BLOCK"]
    reason: str = ""


def _job_key(job_id: str) -> str:
    return f"{JOB_PREFIX}{job_id}"


def _authenticate_api_key(api_key: str | None) -> None:
    expected_key = os.getenv("WEBHOOK_API_KEY")
    if not expected_key:
        raise HTTPException(status_code=503, detail="webhook authentication is not configured")
    if not api_key or not hmac.compare_digest(api_key, expected_key):
        raise HTTPException(status_code=401, detail="invalid API key")


def _enqueue_job(owner: str, repo: str, pr_number: int, head_sha: str) -> dict[str, str | bool]:
    job_id = str(uuid.uuid4())
    dedupe_key = f"{DEDUPE_PREFIX}{owner}:{repo}:{head_sha}"
    job_key = _job_key(job_id)
    job_payload = json.dumps(
        {
            "job_id": job_id,
            "owner": owner,
            "repo": repo,
            "pr_number": pr_number,
            "head_sha": head_sha,
        }
    )
    result = redis_client.eval(
        """local existing = redis.call('GET', KEYS[1])
        if existing then
            local status = redis.call('HGET', 'mergeguard:job:' .. existing, 'status')
            if status == 'queued' or status == 'running' or status == 'awaiting_review' or status == 'review_queued' or status == 'resuming' then
                return existing
            end
            redis.call('DEL', KEYS[1])
        end
        redis.call('SET', KEYS[1], ARGV[1], 'EX', ARGV[6])
        redis.call('HSET', KEYS[2],
            'job_id', ARGV[1],
            'owner', ARGV[2],
            'repo', ARGV[3],
            'pr_number', ARGV[4],
            'head_sha', ARGV[5],
            'status', 'queued',
            'attempts', '0',
            'result', '')
        redis.call('EXPIRE', KEYS[2], ARGV[6])
        redis.call('LPUSH', KEYS[3], ARGV[7])
        return ARGV[1]""",
        3,
        dedupe_key,
        job_key,
        QUEUE_KEY,
        job_id,
        owner,
        repo,
        pr_number,
        head_sha,
        JOB_TTL_SECONDS,
        job_payload,
    )
    result = result.decode() if isinstance(result, bytes) else str(result)
    return {"job_id": result, "status": "queued", "deduplicated": result != job_id}


@app.get("/health")
def health() -> dict[str, str]:
    try:
        redis_client.ping()
    except redis.RedisError as error:
        raise HTTPException(status_code=503, detail="queue unavailable") from error
    return {"status": "ok", "service": "mergeguard"}


@app.get("/metrics")
def metrics() -> dict[str, Any]:
    metrics_data = db.get_metrics_data()
    return {"status": "ok", **build_metrics(**metrics_data)}


@app.post("/webhook/pr", status_code=202)
def webhook_pr(
    payload: PullRequestWebhook,
    x_api_key: str | None = Header(default=None),
) -> dict[str, str | bool]:
    _authenticate_api_key(x_api_key)
    head_sha = payload.head_sha
    if not head_sha:
        pull_request = GitHubClient().get_pull_request(payload.owner, payload.repo, payload.pr_number)
        head_sha = pull_request.get("head", {}).get("sha")
    if not head_sha:
        raise HTTPException(status_code=502, detail="GitHub response did not include the pull request head SHA")
    return _enqueue_job(payload.owner, payload.repo, payload.pr_number, head_sha)


@app.post("/webhook/github", status_code=202)
async def github_webhook(request: Request) -> Response:
    secret = os.getenv("GITHUB_WEBHOOK_SECRET")
    if not secret:
        raise HTTPException(status_code=503, detail="GitHub webhook authentication is not configured")

    raw_body = await request.body()
    provided_signature = request.headers.get("X-Hub-Signature-256", "")
    expected_signature = "sha256=" + hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    if not provided_signature or not hmac.compare_digest(provided_signature, expected_signature):
        raise HTTPException(status_code=401, detail="invalid GitHub webhook signature")

    if request.headers.get("X-GitHub-Event") != "pull_request":
        return Response(status_code=204)
    try:
        payload = json.loads(raw_body)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise HTTPException(status_code=400, detail="invalid webhook JSON") from error
    if payload.get("action") not in {"opened", "synchronize", "reopened"}:
        return Response(status_code=204)

    try:
        owner = payload["repository"]["owner"]["login"]
        repo = payload["repository"]["name"]
        pr_number = int(payload["pull_request"]["number"])
        head_sha = payload["pull_request"]["head"]["sha"]
    except (KeyError, TypeError, ValueError) as error:
        raise HTTPException(status_code=400, detail="pull request webhook payload is incomplete") from error
    if not owner or not repo or not head_sha:
        raise HTTPException(status_code=400, detail="pull request webhook payload is incomplete")

    result = _enqueue_job(owner, repo, pr_number, head_sha)
    return Response(
        content=json.dumps(result),
        status_code=202,
        media_type="application/json",
    )


@app.post("/pr/{job_id}/review", status_code=202)
def submit_human_review(
    job_id: str,
    payload: HumanReviewRequest,
    x_api_key: str | None = Header(default=None),
) -> dict[str, str]:
    _authenticate_api_key(x_api_key)
    job = redis_client.hgetall(_job_key(job_id))
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    if job.get("status") != "awaiting_review":
        raise HTTPException(status_code=409, detail="job is not awaiting human review")

    review_payload = json.loads(job.get("review_payload", "{}"))
    is_override = payload.decision != review_payload.get("verdict")
    reason = payload.reason.strip()
    if is_override and not reason:
        raise HTTPException(status_code=422, detail="a reason is required when overriding the verdict")

    resume_job = json.dumps(
        {
            "action": "resume",
            "job_id": job_id,
            "decision": payload.decision,
            "reason": reason,
        }
    )
    queued = redis_client.eval(
        """if redis.call('HGET', KEYS[1], 'status') ~= 'awaiting_review' then return 0 end
        redis.call('HSET', KEYS[1], 'status', 'review_queued')
        redis.call('LPUSH', KEYS[2], ARGV[1])
        return 1""",
        2,
        _job_key(job_id),
        QUEUE_KEY,
        resume_job,
    )
    if queued != 1:
        raise HTTPException(status_code=409, detail="job is not awaiting human review")

    try:
        db.record_human_review(
            job_id=job_id,
            decision=payload.decision,
            human_override=is_override,
            override_reason=reason or None,
        )
    except Exception:
        logger.exception("Could not record queued human decision for job %s", job_id)
    return {"job_id": job_id, "status": "review_queued"}


@app.get("/pr/{job_id}/status")
def job_status(job_id: str) -> dict[str, Any]:
    job = redis_client.hgetall(_job_key(job_id))
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    if job.get("result"):
        job["result"] = json.loads(job["result"])
    if job.get("status") == "awaiting_review" and job.get("review_payload"):
        job["review_payload"] = json.loads(job["review_payload"])
    else:
        job.pop("review_payload", None)
    if "pr_number" in job:
        job["pr_number"] = int(job["pr_number"])
    return job