from __future__ import annotations

import operator
import os
import threading
import time
from typing import Annotated, Any, Literal, TypedDict

from pydantic import BaseModel, Field

_rate_lock = threading.Lock()
_last_request_at = 0.0


def _rate_limit() -> None:
    global _last_request_at
    minimum_interval = max(0.0, float(os.getenv("GEMINI_MIN_REQUEST_INTERVAL_SECONDS", "1.0")))
    with _rate_lock:
        now = time.monotonic()
        delay = minimum_interval - (now - _last_request_at)
        if delay > 0:
            time.sleep(delay)
        _last_request_at = time.monotonic()


class RiskFinding(BaseModel):
    severity: Literal["low", "medium", "high"] = "low"
    description: str = Field(..., min_length=1)
    line_reference: str = "unknown"


class SecurityFinding(BaseModel):
    severity: Literal["low", "medium", "high", "critical"] = "low"
    description: str = Field(..., min_length=1)
    package_name: str = "unknown"


class MergeGuardState(TypedDict, total=False):
    job_id: str
    no_human: bool
    owner: str
    repo: str
    pr_number: int
    pr_title: str
    pr_body: str
    pr_comments: list[dict[str, Any]]
    pr_diff: str
    head_sha: str
    changed_files: list[str]
    injection_flags: list[str]
    agents_skipped: Annotated[list[str], operator.add]
    code_findings: list[RiskFinding]
    test_results: list[dict[str, Any]]
    security_findings: list[SecurityFinding]
    reasons: Annotated[list[str], operator.add]
    verdict: str
    confidence: float
    requires_human_approval: bool
    human_approved: bool | None
    review_status: str
    final_verdict: str | None
    human_override: bool | None
    override_reason: str | None


def _extract_risk_line(diff: str) -> str:
    for line in diff.splitlines():
        if line.startswith("+") or line.startswith("-"):
            stripped = line[1:].strip()
            if stripped:
                return stripped[:80]
    return "diff:unknown"


def analyze_code_risk_heuristic(diff: str, context: str | None = None) -> list[RiskFinding]:
    combined = f"{diff}\n{context or ''}".lower()
    findings: list[RiskFinding] = []

    if any(term in combined for term in ["token", "auth", "session", "permission", "user", "null"]):
        findings.append(
            RiskFinding(
                severity="medium",
                description="[heuristic] Possible auth or access-control issue: the PR changes token/session logic or user access assumptions without an obvious guard.",
                line_reference=_extract_risk_line(diff),
            )
        )

    if any(term in combined for term in ["delete", "drop", "update", "query", "db"]):
        findings.append(
            RiskFinding(
                severity="high",
                description="[heuristic] Potential data integrity or destructive operation risk detected in the PR diff.",
                line_reference=_extract_risk_line(diff),
            )
        )

    if not findings:
        findings.append(
            RiskFinding(
                severity="low",
                description="[heuristic] No obvious logic risk detected in the provided diff; manual review is still recommended.",
                line_reference="diff:unknown",
            )
        )

    return findings


