from __future__ import annotations

import logging
import os
import re
from contextlib import contextmanager
from threading import Lock
from typing import Any

from mergeguard.storage import db

RecordEntry = dict[str, Any]
logger = logging.getLogger(__name__)
_langfuse_client = None
_langfuse_lock = Lock()


def _get_langfuse_client():
    global _langfuse_client
    if not os.getenv("LANGFUSE_PUBLIC_KEY") or not os.getenv("LANGFUSE_SECRET_KEY"):
        return None
    if _langfuse_client is not None:
        return _langfuse_client
    with _langfuse_lock:
        if _langfuse_client is None:
            try:
                from langfuse import Langfuse

                _langfuse_client = Langfuse(
                    public_key=os.environ["LANGFUSE_PUBLIC_KEY"],
                    secret_key=os.environ["LANGFUSE_SECRET_KEY"],
                    host=os.getenv("LANGFUSE_HOST") or os.getenv("LANGFUSE_BASE_URL"),
                    enabled=True,
                )
            except Exception:
                logger.warning("Langfuse tracing could not be initialized", exc_info=True)
                return None
    return _langfuse_client


def start_job_trace(job_id: str) -> None:
    client = _get_langfuse_client()
    if client is None:
        return
    try:
        client.trace(id=job_id, name="mergeguard-review", metadata={"job_id": job_id})
    except Exception:
        logger.warning("Could not start Langfuse trace", exc_info=True)


def finish_job_trace(job_id: str, *, status: str, verdict: str | None = None) -> None:
    client = _get_langfuse_client()
    if client is None:
        return
    try:
        client.trace(id=job_id).update(
            output={"status": status, "verdict": verdict} if verdict else {"status": status}
        )
        client.flush()
    except Exception:
        logger.warning("Could not finish Langfuse trace", exc_info=True)


@contextmanager
def trace_observation(
    job_id: str,
    name: str,
    *,
    generation: bool = False,
    model: str | None = None,
):
    observation = None
    client = _get_langfuse_client()
    if client is not None:
        try:
            trace = client.trace(id=job_id, name="mergeguard-review", metadata={"job_id": job_id})
            if generation:
                observation = trace.generation(name=name, model=model)
            else:
                observation = trace.span(name=name, metadata={"job_id": job_id})
        except Exception:
            logger.warning("Could not create Langfuse observation %s", name, exc_info=True)

    try:
        yield observation
    except Exception as error:
        update_observation(observation, level="ERROR", status_message=type(error).__name__)
        raise
    finally:
        if observation is not None:
            try:
                observation.end()
            except Exception:
                logger.warning("Could not end Langfuse observation %s", name, exc_info=True)


def update_observation(observation, **values: Any) -> None:
    if observation is None:
        return
    try:
        observation.update(**_redact_trace_values(values))
    except Exception:
        logger.warning("Could not update Langfuse observation", exc_info=True)


def _redact_trace_values(value: Any) -> Any:
    if isinstance(value, str):
        redacted = value
        for variable in ("GITHUB_TOKEN", "GEMINI_API_KEY", "WEBHOOK_API_KEY", "LANGFUSE_SECRET_KEY"):
            secret = os.getenv(variable)
            if secret:
                redacted = redacted.replace(secret, "[REDACTED]")
        redacted = re.sub(
            r"\b(?:gh[pousr]_[A-Za-z0-9_]{20,}|AIza[\w-]{20,}|sk-lf-[\w-]+)\b",
            "[REDACTED]",
            redacted,
        )
        redacted = re.sub(
            r"(?i)\b(?:api[_ -]?key|secret|token|password)\s*[:=]\s*[^\s,;]+",
            "[REDACTED]",
            redacted,
        )
        return re.sub(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{12,}", "Bearer [REDACTED]", redacted)
    if isinstance(value, list):
        return [_redact_trace_values(item) for item in value]
    if isinstance(value, tuple):
        return [_redact_trace_values(item) for item in value]
    if isinstance(value, dict):
        return {key: _redact_trace_values(item) for key, item in value.items()}
    return value


def record_tool_call(job_id: str, tool: str, fn):
    with trace_observation(job_id, tool) as observation:
        try:
            result = db.record_tool_event(job_id, tool, fn)
        except Exception as error:
            update_observation(
                observation,
                output={"status": "failed"},
                level="ERROR",
                status_message=type(error).__name__,
            )
            raise
        update_observation(observation, output={"status": "succeeded"})
        return result


def describe_agent_decision(agent: str, status: str, reason: str) -> dict[str, str]:
    return {
        "agent": agent,
        "status": status,
        "reason": reason,
    }


def build_history_entry(
    *,
    owner: str,
    repo: str,
    pr_number: int,
    verdict: str,
    cost_saved: float | None = None,
    human_override: bool | None = None,
    reasoning: str | None = None,
    agent_decisions: dict[str, dict[str, str]] | None = None,
) -> RecordEntry:
    return {
        "owner": owner,
        "repo": repo,
        "pr_number": pr_number,
        "verdict": verdict,
        "cost_saved": cost_saved,
        "human_override": human_override,
        "reasoning": reasoning,
        "agent_decisions": agent_decisions or {},
    }


class RunHistory:
    def add(
        self,
        *,
        owner: str,
        repo: str,
        pr_number: int,
        verdict: str,
        human_override: bool | None = None,
        reasoning: str | None = None,
        agent_decisions: dict[str, dict[str, str]] | None = None,
        cost_saved: float | None = None,
    ) -> RecordEntry:
        entry = build_history_entry(
            owner=owner,
            repo=repo,
            pr_number=pr_number,
            verdict=verdict,
            cost_saved=cost_saved,
            human_override=human_override,
            reasoning=reasoning,
            agent_decisions=agent_decisions,
        )
        import uuid

        job_id = str(uuid.uuid4())
        db.create_run(job_id=job_id, owner=owner, repo=repo, pr_number=pr_number)
        db.finish_run(
            job_id=job_id,
            status="completed",
            verdict=verdict,
            final_verdict=verdict,
            human_override=human_override,
            reasons=[reasoning] if reasoning else [],
            findings={"agent_decisions": agent_decisions or {}},
            cost_saved_usd=str(cost_saved) if cost_saved is not None else None,
        )
        return entry

    def latest(self) -> RecordEntry:
        entries = db.get_run_history(limit=1)
        if not entries:
            raise LookupError("No run history entries are available.")
        return self._as_entry(entries[0])

    def entries(self) -> list[RecordEntry]:
        return [self._as_entry(entry) for entry in reversed(db.get_run_history())]

    @staticmethod
    def _as_entry(row: dict[str, Any]) -> RecordEntry:
        reasons = row.get("reasons") or []
        findings = row.get("findings") or {}
        return {
            "owner": row["owner"],
            "repo": row["repo"],
            "pr_number": row["pr_number"],
            "verdict": row.get("final_verdict") or row.get("verdict"),
            "cost_saved": float(row["cost_saved_usd"]) if row.get("cost_saved_usd") is not None else None,
            "human_override": row.get("human_override"),
            "reasoning": reasons[0] if reasons else None,
            "agent_decisions": findings.get("agent_decisions", {}),
        }


def calculate_run_metrics(run_records: list[dict[str, Any]], agents: tuple[str, ...] = ("code_analysis", "test_execution", "security_review")) -> dict[str, float]:
    total_agents = len(agents)
    total_skipped = 0
    total_cost_saved = 0.0

    for record in run_records:
        skipped = record.get("agents_skipped", [])
        total_skipped += len(skipped)
        cost_saved = record.get("cost_saved_usd", record.get("cost_saved"))
        if cost_saved is not None:
            total_cost_saved += float(cost_saved)

    total_runs = max(len(run_records), 1)
    skipped_pct = (total_skipped / (total_runs * total_agents)) * 100.0

    return {
        "agents_skipped_pct": round(skipped_pct, 2),
        "cost_saved_total": round(total_cost_saved, 2),
    }


def should_skip_security_review(changed_files: list[str]) -> bool:
    dependency_paths = {
        "requirements.txt",
        "pyproject.toml",
        "poetry.lock",
        "package.json",
        "package-lock.json",
        "yarn.lock",
        "pipfile",
        "pipfile.lock",
    }

    if not changed_files:
        return True

    normalized = {os.path.basename(path.replace("\\", "/")).lower() for path in changed_files}
    has_dependency_file = any(
        name in dependency_paths or (name.startswith("requirements") and name.endswith(".txt"))
        for name in normalized
    )
    return not has_dependency_file


__all__ = [
    "RecordEntry",
    "RunHistory",
    "build_history_entry",
    "calculate_run_metrics",
    "describe_agent_decision",
    "finish_job_trace",
    "record_tool_call",
    "start_job_trace",
    "should_skip_security_review",
    "trace_observation",
    "update_observation",
]
