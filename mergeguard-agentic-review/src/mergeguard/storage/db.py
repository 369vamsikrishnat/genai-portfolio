from __future__ import annotations

import json
import logging
import os
import time
from collections.abc import Callable
from typing import Any, TypeVar

logger = logging.getLogger(__name__)
ResultT = TypeVar("ResultT")

SCHEMA_STATEMENTS = (
    """CREATE TABLE IF NOT EXISTS runs (
        job_id uuid PRIMARY KEY,
        owner text NOT NULL,
        repo text NOT NULL,
        pr_number integer NOT NULL,
        head_sha text,
        verdict text,
        confidence real,
        final_verdict text,
        human_override boolean,
        override_reason text,
        review_status text,
        status text NOT NULL,
        agents_skipped text[] NOT NULL DEFAULT '{}',
        reasons jsonb NOT NULL DEFAULT '[]'::jsonb,
        findings jsonb NOT NULL DEFAULT '{}'::jsonb,
        cost_saved_usd numeric,
        started_at timestamptz NOT NULL DEFAULT now(),
        finished_at timestamptz
    )""",
    """CREATE TABLE IF NOT EXISTS tool_events (
        id serial PRIMARY KEY,
        job_id uuid NOT NULL,
        tool text NOT NULL,
        success boolean NOT NULL,
        error text,
        latency_ms integer NOT NULL,
        created_at timestamptz NOT NULL DEFAULT now()
    )""",
)


def _connect():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured.")
    import psycopg

    return psycopg.connect(database_url)


def init_db() -> None:
    with _connect() as connection:
        with connection.cursor() as cursor:
            for statement in SCHEMA_STATEMENTS:
                cursor.execute(statement)


def create_run(*, job_id: str, owner: str, repo: str, pr_number: int) -> None:
    with _connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """INSERT INTO runs (job_id, owner, repo, pr_number, status)
                VALUES (%s, %s, %s, %s, 'running')
                ON CONFLICT (job_id) DO UPDATE SET status = 'running', finished_at = NULL""",
                (job_id, owner, repo, pr_number),
            )


def finish_run(
    *,
    job_id: str,
    status: str,
    head_sha: str | None = None,
    verdict: str | None = None,
    confidence: float | None = None,
    final_verdict: str | None = None,
    human_override: bool | None = None,
    override_reason: str | None = None,
    review_status: str | None = None,
    agents_skipped: list[str] | None = None,
    reasons: list[str] | None = None,
    findings: dict[str, Any] | None = None,
    cost_saved_usd: str | None = None,
) -> None:
    with _connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """UPDATE runs SET
                    head_sha = %s,
                    verdict = %s,
                    confidence = %s,
                    final_verdict = %s,
                    human_override = %s,
                    override_reason = %s,
                    review_status = %s,
                    status = %s,
                    agents_skipped = %s,
                    reasons = %s::jsonb,
                    findings = %s::jsonb,
                    cost_saved_usd = %s,
                    finished_at = now()
                WHERE job_id = %s""",
                (
                    head_sha,
                    verdict,
                    confidence,
                    final_verdict,
                    human_override,
                    override_reason,
                    review_status,
                    status,
                    agents_skipped or [],
                    json.dumps(reasons or []),
                    json.dumps(findings or {}),
                    cost_saved_usd,
                    job_id,
                ),
            )


def record_human_review(
    *,
    job_id: str,
    decision: str,
    human_override: bool,
    override_reason: str | None,
) -> None:
    with _connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """UPDATE runs SET
                    final_verdict = %s,
                    human_override = %s,
                    override_reason = %s,
                    review_status = 'review_queued'
                WHERE job_id = %s""",
                (decision, human_override, override_reason, job_id),
            )


def record_tool_event(job_id: str, tool: str, fn: Callable[[], ResultT]) -> ResultT:
    started = time.perf_counter()
    try:
        result = fn()
    except Exception as error:
        _insert_tool_event(
            job_id=job_id,
            tool=tool,
            success=False,
            error=type(error).__name__,
            latency_ms=_elapsed_ms(started),
        )
        raise
    _insert_tool_event(
        job_id=job_id,
        tool=tool,
        success=True,
        error=None,
        latency_ms=_elapsed_ms(started),
    )
    return result


def _elapsed_ms(started: float) -> int:
    return max(0, int((time.perf_counter() - started) * 1000))


def _insert_tool_event(*, job_id: str, tool: str, success: bool, error: str | None, latency_ms: int) -> None:
    if not os.getenv("DATABASE_URL"):
        return
    try:
        with _connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """INSERT INTO tool_events (job_id, tool, success, error, latency_ms)
                    VALUES (%s, %s, %s, %s, %s)""",
                    (job_id, tool, success, error, latency_ms),
                )
    except Exception:
        logger.warning("Could not persist tool event for %s", tool, exc_info=True)


def get_run_history(*, limit: int | None = None) -> list[dict[str, Any]]:
    query = "SELECT * FROM runs ORDER BY started_at"
    parameters: tuple[Any, ...] = ()
    if limit is not None:
        query += " LIMIT %s"
        parameters = (limit,)
    with _connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, parameters)
            column_names = [column.name for column in cursor.description]
            return [dict(zip(column_names, row, strict=True)) for row in cursor.fetchall()]


def get_metrics_data() -> dict[str, list[dict[str, Any]]]:
    with _connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT success FROM tool_events")
            tool_events = [{"success": row[0]} for row in cursor.fetchall()]
            cursor.execute("SELECT status, human_override, review_status, agents_skipped FROM runs")
            runs = [
                {
                    "status": row[0],
                    "human_override": row[1],
                    "review_status": row[2],
                    "agents_skipped": row[3] or [],
                }
                for row in cursor.fetchall()
            ]
    return {"tool_events": tool_events, "runs": runs}


__all__ = [
    "SCHEMA_STATEMENTS",
    "create_run",
    "finish_run",
    "get_metrics_data",
    "get_run_history",
    "init_db",
    "record_human_review",
    "record_tool_event",
]