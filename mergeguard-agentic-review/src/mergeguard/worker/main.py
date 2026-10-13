from __future__ import annotations

import json
import logging
import os
import re
import shutil
from collections.abc import Callable
from pathlib import Path

import redis
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.types import Command
from pydantic_core import to_jsonable_python

from mergeguard.storage import db
from mergeguard.observability import tracing
from mergeguard.workflow.graph import GRAPH_RECURSION_LIMIT, build_graph
from mergeguard.sandbox.jobs import extract_source_archive
from mergeguard.tools.github_client import GitHubClient


logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)
redis_client = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"), decode_responses=True)
QUEUE_KEY = "mergeguard:review_jobs"
PROCESSING_KEY = "mergeguard:processing"
DEAD_LETTER_KEY = "mergeguard:dead_letter"
JOB_TTL_SECONDS = 7 * 24 * 60 * 60
MAX_JOB_ATTEMPTS = 3


def _redact_secrets(value):
    if isinstance(value, str):
        redacted = value
        for name in ("GITHUB_TOKEN", "GEMINI_API_KEY", "WEBHOOK_API_KEY"):
            secret = os.getenv(name)
            if secret:
                redacted = redacted.replace(secret, "[REDACTED]")
        return re.sub(r"\b(?:gh[pousr]_[A-Za-z0-9_]{20,}|AIza[\w-]{20,})\b", "[REDACTED]", redacted)
    if isinstance(value, list):
        return [_redact_secrets(item) for item in value]
    if isinstance(value, dict):
        return {key: _redact_secrets(item) for key, item in value.items()}
    return value


def _persist_finished_run(job_id: str, result: dict | None, *, status: str, head_sha: str | None = None) -> None:
    result = result or {}
    findings = {
        key: to_jsonable_python(result.get(key, []))
        for key in ("code_findings", "security_findings")
    }
    db.finish_run(
        job_id=job_id,
        status=status,
        head_sha=head_sha,
        verdict=result.get("verdict"),
        confidence=result.get("confidence"),
        final_verdict=result.get("final_verdict"),
        human_override=result.get("human_override"),
        override_reason=result.get("override_reason"),
        review_status=result.get("review_status"),
        agents_skipped=result.get("agents_skipped", []),
        reasons=_redact_secrets(result.get("reasons", [])),
        findings=_redact_secrets(findings),
        cost_saved_usd=None,
    )


def process_job(
    payload: dict[str, object],
    checkpointer=None,
    *,
    no_human: bool = False,
    result_callback: Callable[[dict], None] | None = None,
) -> bool:
    job_id = str(payload["job_id"])
    job_key = f"mergeguard:job:{job_id}"
    tracing.start_job_trace(job_id)
    redis_client.hset(job_key, "status", "running")
    head_sha: str | None = None
    try:
        owner = str(payload["owner"])
        repo = str(payload["repo"])
        pr_number = int(payload["pr_number"])
        db.create_run(job_id=job_id, owner=owner, repo=repo, pr_number=pr_number)
        github = GitHubClient()
        pull_request = tracing.record_tool_call(
            job_id,
            "github.get_pull_request",
            lambda: github.get_pull_request(owner, repo, pr_number),
        )
        files = tracing.record_tool_call(
            job_id,
            "github.get_changed_files",
            lambda: github.get_changed_files(owner, repo, pr_number),
        )
        pr_comments = tracing.record_tool_call(
            job_id,
            "github.get_pr_conversation",
            lambda: github.get_pr_conversation(owner, repo, pr_number),
        )
        head_sha = pull_request.get("head", {}).get("sha")
        if not head_sha:
            raise ValueError("GitHub response did not include the pull request head SHA.")
        pr_diff = "\n\n".join(
            f"File: {file.get('filename', 'unknown')}\n{file.get('patch', '[patch unavailable]')}"
            for file in files
        )
        workspace = Path(os.getenv("SANDBOX_WORKSPACE_DIR", "/sandbox/workspaces")) / job_id
        try:
            source_archive = tracing.record_tool_call(
                job_id,
                "github.get_source_archive",
                lambda: github.get_source_archive(owner, repo, head_sha),
            )
            extract_source_archive(source_archive, workspace)
            result = build_graph().compile(checkpointer=checkpointer).invoke(
                {
                    "job_id": job_id,
                    "no_human": no_human,
                    "owner": owner,
                    "repo": repo,
                    "pr_number": pr_number,
                    "head_sha": head_sha,
                    "pr_diff": pr_diff,
                    "pr_title": pull_request.get("title", ""),
                    "pr_body": pull_request.get("body") or "",
                    "pr_comments": pr_comments,
                    "changed_files": [file.get("filename", "") for file in files],
                },
                config={
                    "configurable": {"thread_id": job_id},
                    "recursion_limit": GRAPH_RECURSION_LIMIT,
                },
            )
            if result_callback is not None:
                result_callback(result)
        finally:
            shutil.rmtree(workspace, ignore_errors=True)
        interrupts = result.get("__interrupt__", [])
        if interrupts:
            interrupt_value = interrupts[0].value
            review_payload = to_jsonable_python(interrupt_value)
            redis_client.hset(
                job_key,
                mapping={
                    "status": "awaiting_review",
                    "review_payload": json.dumps(review_payload),
                    "result": json.dumps({"review": review_payload}),
                },
            )
            _persist_finished_run(
                job_id,
                {**result, "review_status": "awaiting_review"},
                status="awaiting_review",
                head_sha=head_sha,
            )
            tracing.finish_job_trace(job_id, status="awaiting_review", verdict=result.get("verdict"))
            return True
        redis_client.hset(
            job_key,
            mapping={"status": "completed", "result": json.dumps(to_jsonable_python(result))},
        )
        _persist_finished_run(job_id, result, status="completed", head_sha=head_sha)
        tracing.finish_job_trace(job_id, status="completed", verdict=result.get("verdict"))
        return True
    except Exception as error:
        logger.exception("Review job %s failed", job_id)
        redis_client.hset(
            job_key,
            mapping={"last_error": type(error).__name__},
        )
        tracing.finish_job_trace(job_id, status="failed")
        return False


def resume_job(payload: dict[str, object], checkpointer) -> bool:
    job_id = str(payload["job_id"])
    job_key = f"mergeguard:job:{job_id}"
    job = redis_client.hgetall(job_key)
    if job.get("status") not in {"review_queued", "resuming"}:
        logger.warning("Ignoring resume for job %s that is not queued for review", job_id)
        return True

    decision = str(payload["decision"])
    reason = str(payload.get("reason", "")).strip()
    if decision not in {"MERGE", "MERGE_WITH_COMMENTS", "BLOCK"}:
        raise ValueError("Human review decision is not allowed.")
    if decision != json.loads(job.get("review_payload", "{}" )).get("verdict") and not reason:
        raise ValueError("A reason is required when overriding the automated verdict.")

    try:
        result = build_graph().compile(checkpointer=checkpointer).invoke(
            Command(resume={"decision": decision, "reason": reason}),
            config={
                "configurable": {"thread_id": job_id},
                "recursion_limit": GRAPH_RECURSION_LIMIT,
            },
        )
        redis_client.hset(
            job_key,
            mapping={"status": "completed", "result": json.dumps(to_jsonable_python(result))},
        )
        _persist_finished_run(
            job_id,
            result,
            status="completed",
            head_sha=result.get("head_sha"),
        )
        tracing.finish_job_trace(job_id, status="completed", verdict=result.get("verdict"))
        return True
    except Exception as error:
        logger.exception("Could not resume review for job %s", job_id)
        redis_client.hset(job_key, mapping={"last_error": type(error).__name__})
        tracing.finish_job_trace(job_id, status="failed")
        return False


def _raw_text(value: str | bytes) -> str:
    return value.decode() if isinstance(value, bytes) else value


def _job_key_for_payload(payload: dict[str, object]) -> str:
    return f"mergeguard:job:{payload['job_id']}"


def _start_job_attempt(payload: dict[str, object]) -> int:
    job_key = _job_key_for_payload(payload)
    attempts = redis_client.hincrby(job_key, "attempts", 1)
    redis_client.expire(job_key, JOB_TTL_SECONDS)
    status = "resuming" if payload.get("action") == "resume" else "running"
    redis_client.hset(job_key, "status", status)
    return int(attempts)


def _finish_failed_attempt(raw_job: str, payload: dict[str, object], attempts: int) -> None:
    job_key = _job_key_for_payload(payload)
    current_job = redis_client.hgetall(job_key)
    error_name = current_job.get("last_error", "WorkerError")
    if attempts >= MAX_JOB_ATTEMPTS:
        redis_client.eval(
            """redis.call('LREM', KEYS[1], 1, ARGV[1])
            redis.call('LPUSH', KEYS[2], ARGV[1])
            redis.call('HSET', KEYS[3], 'status', 'failed', 'attempts', ARGV[2])
            redis.call('EXPIRE', KEYS[3], ARGV[3])
            return 1""",
            3,
            PROCESSING_KEY,
            DEAD_LETTER_KEY,
            job_key,
            raw_job,
            attempts,
            JOB_TTL_SECONDS,
        )
        try:
            _persist_finished_run(
                str(payload["job_id"]),
                {"reasons": [f"worker failed after {attempts} attempts: {error_name}"]},
                status="failed",
            )
        except Exception:
            logger.exception("Could not persist dead-letter run %s", payload.get("job_id"))
        return

    redis_client.eval(
        """redis.call('LREM', KEYS[1], 1, ARGV[1])
        redis.call('LPUSH', KEYS[2], ARGV[1])
        redis.call('HSET', KEYS[3], 'status', 'queued', 'attempts', ARGV[2])
        redis.call('EXPIRE', KEYS[3], ARGV[3])
        return 1""",
        3,
        PROCESSING_KEY,
        QUEUE_KEY,
        job_key,
        raw_job,
        attempts,
        JOB_TTL_SECONDS,
    )


def recover_processing_jobs() -> int:
    recovered = 0
    while True:
        raw_job = redis_client.lindex(PROCESSING_KEY, -1)
        if raw_job is None:
            return recovered
        raw_job = _raw_text(raw_job)
        try:
            payload = json.loads(raw_job)
            attempts = int(redis_client.hgetall(_job_key_for_payload(payload)).get("attempts", 0))
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            redis_client.lmove(PROCESSING_KEY, DEAD_LETTER_KEY, "RIGHT", "LEFT")
            continue
        if attempts >= MAX_JOB_ATTEMPTS:
            job_key = _job_key_for_payload(payload)
            redis_client.eval(
                """redis.call('LREM', KEYS[1], 1, ARGV[1])
                redis.call('LPUSH', KEYS[2], ARGV[1])
                redis.call('HSET', KEYS[3], 'status', 'failed')
                redis.call('EXPIRE', KEYS[3], ARGV[2])
                return 1""",
                3,
                PROCESSING_KEY,
                DEAD_LETTER_KEY,
                job_key,
                raw_job,
                JOB_TTL_SECONDS,
            )
            try:
                _persist_finished_run(
                    str(payload["job_id"]),
                    {"reasons": [f"worker failed after {attempts} attempts"]},
                    status="failed",
                )
            except Exception:
                logger.exception("Could not persist recovered dead-letter run %s", payload.get("job_id"))
            continue
        redis_client.lmove(PROCESSING_KEY, QUEUE_KEY, "RIGHT", "LEFT")
        recovered += 1


def process_queue_item(raw_job: str | bytes, checkpointer) -> None:
    raw_job = _raw_text(raw_job)
    try:
        payload = json.loads(raw_job)
    except json.JSONDecodeError:
        redis_client.lrem(PROCESSING_KEY, 1, raw_job)
        redis_client.lpush(DEAD_LETTER_KEY, raw_job)
        logger.exception("Moved malformed queue item to dead letter")
        return

    try:
        attempts = _start_job_attempt(payload)
    except (KeyError, TypeError, ValueError):
        redis_client.lrem(PROCESSING_KEY, 1, raw_job)
        redis_client.lpush(DEAD_LETTER_KEY, raw_job)
        logger.exception("Moved malformed job to dead letter")
        return

    succeeded = (
        resume_job(payload, checkpointer)
        if payload.get("action") == "resume"
        else process_job(payload, checkpointer)
    )
    if succeeded:
        redis_client.lrem(PROCESSING_KEY, 1, raw_job)
        return
    _finish_failed_attempt(raw_job, payload, attempts)


def run_worker() -> None:
    logger.info("MergeGuard worker started")
    db.init_db()
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is required for persistent human review.")
    with PostgresSaver.from_conn_string(database_url) as checkpointer:
        checkpointer.setup()
        recover_processing_jobs()
        while True:
            try:
                item = redis_client.blmove(QUEUE_KEY, PROCESSING_KEY, 5, src="RIGHT", dest="LEFT")
            except redis.RedisError:
                logger.exception("Queue connection failed; retrying")
                continue
            if item is None:
                continue
            process_queue_item(item, checkpointer)


if __name__ == "__main__":
    run_worker()