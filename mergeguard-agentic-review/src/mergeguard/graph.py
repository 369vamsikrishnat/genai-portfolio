from __future__ import annotations

from typing import Any, Literal, TypedDict

from langgraph.graph import START, END, StateGraph
from pydantic import BaseModel, Field

from .tools.sandbox import SandboxedTestRunner


class RiskFinding(BaseModel):
    severity: Literal["low", "medium", "high"] = "low"
    description: str = Field(..., min_length=1)
    line_reference: str = "unknown"


class SecurityFinding(BaseModel):
    severity: Literal["low", "medium", "high", "critical"] = "low"
    description: str = Field(..., min_length=1)
    package_name: str = "unknown"


class MergeGuardState(TypedDict, total=False):
    owner: str
    repo: str
    pr_number: int
    pr_title: str
    pr_diff: str
    code_findings: list[RiskFinding]
    test_results: list[dict[str, Any]]
    security_findings: list[SecurityFinding]
    verdict: str
    confidence: float


def _extract_risk_line(diff: str) -> str:
    for line in diff.splitlines():
        if line.startswith("+") or line.startswith("-"):
            stripped = line[1:].strip()
            if stripped:
                return stripped[:80]
    return "diff:unknown"


def analyze_code_risk(diff: str, context: str | None = None) -> list[RiskFinding]:
    combined = f"{diff}\n{context or ''}".lower()
    findings: list[RiskFinding] = []

    if any(term in combined for term in ["token", "auth", "session", "permission", "user", "null"]):
        findings.append(
            RiskFinding(
                severity="medium",
                description="Possible auth or access-control issue: the PR changes token/session logic or user access assumptions without an obvious guard.",
                line_reference=_extract_risk_line(diff),
            )
        )

    if any(term in combined for term in ["delete", "drop", "update", "query", "db"]):
        findings.append(
            RiskFinding(
                severity="high",
                description="Potential data integrity or destructive operation risk detected in the PR diff.",
                line_reference=_extract_risk_line(diff),
            )
        )

    if not findings:
        findings.append(
            RiskFinding(
                severity="low",
                description="No obvious logic risk detected in the provided diff; manual review is still recommended.",
                line_reference="diff:unknown",
            )
        )

    return findings


def analyze_security_risk(diff: str, package_names: list[str] | None = None) -> list[SecurityFinding]:
    package_names = package_names or ["requests", "django", "jinja2", "flask"]
    findings: list[SecurityFinding] = []
    lower_diff = diff.lower()

    for package in package_names:
        if package in lower_diff:
            findings.append(
                SecurityFinding(
                    severity="high",
                    description=f"Dependency package '{package}' appears in the PR diff and should be reviewed for security impact.",
                    package_name=package,
                )
            )

    if not findings:
        findings.append(
            SecurityFinding(
                severity="low",
                description="No dependency security concern detected in the current diff.",
                package_name="unknown",
            )
        )

    return findings


def combine_verdict(
    code_findings: list[dict[str, Any]] | None = None,
    test_results: list[dict[str, Any]] | None = None,
    security_findings: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    code_findings = code_findings or []
    test_results = test_results or []
    security_findings = security_findings or []

    highest_code = max((item.get("severity", "low") for item in code_findings), default="low", key=lambda s: ["low", "medium", "high"].index(s))
    highest_security = max((item.get("severity", "low") for item in security_findings), default="low", key=lambda s: ["low", "medium", "high", "critical"].index(s))

    failed_tests = any(item.get("status") == "failed" for item in test_results)

    if highest_security == "critical" or failed_tests:
        verdict = "BLOCK"
        confidence = 0.9
    elif highest_code == "high" or highest_security == "high":
        verdict = "MERGE_WITH_COMMENTS"
        confidence = 0.8
    else:
        verdict = "MERGE"
        confidence = 0.72

    return {"verdict": verdict, "confidence": confidence}


def code_analysis_node(state: MergeGuardState) -> MergeGuardState:
    pr_diff = state.get("pr_diff", "")
    context = state.get("pr_title", "")
    state["code_findings"] = analyze_code_risk(pr_diff, context)
    return state


def test_execution_node(state: MergeGuardState) -> MergeGuardState:
    runner = SandboxedTestRunner()
    result = runner.run_tests(
        repo_path=".",
        command=["python", "-m", "pytest", "tests/test_day20_graph.py", "-q"],
    )
    state["test_results"] = [result.model_dump()]
    return state


def security_review_node(state: MergeGuardState) -> MergeGuardState:
    pr_diff = state.get("pr_diff", "")
    state["security_findings"] = analyze_security_risk(pr_diff)
    return state


def orchestrator_node(state: MergeGuardState) -> MergeGuardState:
    result = combine_verdict(
        code_findings=[item.model_dump() for item in state.get("code_findings", [])],
        test_results=state.get("test_results", []),
        security_findings=[item.model_dump() for item in state.get("security_findings", [])],
    )
    state["verdict"] = result["verdict"]
    state["confidence"] = result["confidence"]
    return state


def build_graph():
    graph = StateGraph(MergeGuardState)
    graph.add_node("code_analysis", code_analysis_node)
    graph.add_node("test_execution", test_execution_node)
    graph.add_node("security_review", security_review_node)
    graph.add_node("orchestrator", orchestrator_node)
    graph.add_edge(START, "code_analysis")
    graph.add_edge("code_analysis", "test_execution")
    graph.add_edge("test_execution", "security_review")
    graph.add_edge("security_review", "orchestrator")
    graph.add_edge("orchestrator", END)
    return graph
