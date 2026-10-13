from __future__ import annotations

from collections import Counter
from typing import Any


def _percentage(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return round((numerator / denominator) * 100, 2)


def compute_success_rate(tool_events: list[dict[str, Any]]) -> float | None:
    successful = sum(1 for event in tool_events if event.get("success") is True)
    return _percentage(successful, len(tool_events))


def compute_completion_rate(runs: list[dict[str, Any]]) -> float | None:
    completed = sum(
        1 for run in runs
        if run.get("status") == "completed" or run.get("completed") is True
    )
    return _percentage(completed, len(runs))


def compute_override_rate(reviews: list[dict[str, Any]]) -> float | None:
    if any("review_status" in review for review in reviews):
        reviewed = [review for review in reviews if review.get("review_status") == "human_reviewed"]
    else:
        reviewed = [review for review in reviews if review.get("human_override") is not None]
    overrides = sum(1 for review in reviewed if review.get("human_override") is True)
    return _percentage(overrides, len(reviewed))


def compute_agents_skipped_pct(
    runs: list[dict[str, Any]],
    agents: tuple[str, ...] = ("code_analysis", "test_execution", "security_review"),
) -> float | None:
    total_agent_runs = len(runs) * len(agents)
    total_skipped = sum(len(run.get("agents_skipped") or []) for run in runs)
    return _percentage(total_skipped, total_agent_runs)


def summarize_run_metrics(
    *,
    tool_events: list[dict[str, Any]],
    runs: list[dict[str, Any]],
    reviews: list[dict[str, Any]],
) -> dict[str, float | None]:
    return {
        "tool_success_rate": compute_success_rate(tool_events),
        "task_completion_rate": compute_completion_rate(runs),
        "human_override_rate": compute_override_rate(reviews),
    }


def build_metrics(
    *,
    tool_events: list[dict[str, Any]],
    runs: list[dict[str, Any]],
) -> dict[str, Any]:
    summary = summarize_run_metrics(tool_events=tool_events, runs=runs, reviews=runs)
    summary["agents_skipped_pct"] = compute_agents_skipped_pct(runs)
    summary["jobs_by_status"] = dict(Counter(run["status"] for run in runs if run.get("status")))
    summary["total_runs"] = len(runs)
    return summary


__all__ = [
    "compute_completion_rate",
    "compute_agents_skipped_pct",
    "compute_override_rate",
    "compute_success_rate",
    "build_metrics",
    "summarize_run_metrics",
]
