from __future__ import annotations

from typing import Any

from langgraph.graph import START, END, StateGraph
from langgraph.types import RetryPolicy, interrupt

from ..agents import code_analysis_node, security_review_node, test_execution_node
from ..agents.common import (
    MergeGuardState,
    RiskFinding,
    SecurityFinding,
    analyze_code_risk_heuristic,
)
from ..guardrails.injection import detect_prompt_injection

LOW_CONFIDENCE_THRESHOLD = 0.6
GRAPH_RECURSION_LIMIT = 50


def combine_verdict(
    code_findings: list[dict[str, Any]] | None = None,
    test_results: list[dict[str, Any]] | None = None,
    security_findings: list[dict[str, Any]] | None = None,
    injection_flags: list[str] | None = None,
) -> dict[str, Any]:
    code_findings = code_findings or []
    test_results = test_results or []
    security_findings = security_findings or []
    injection_flags = injection_flags or []

    highest_code = max((item.get("severity", "low") for item in code_findings), default="low", key=lambda s: ["low", "medium", "high"].index(s))
    highest_security = max((item.get("severity", "low") for item in security_findings), default="low", key=lambda s: ["low", "medium", "high", "critical"].index(s))

    failed_tests = any(item.get("status") == "failed" for item in test_results)
    test_errors = [item for item in test_results if item.get("status") == "error"]
    reasons: list[str] = []

    if failed_tests:
        reasons.append("tests failed")
    if injection_flags:
        reasons.append("suspected prompt injection in PR content")
    for result in test_results:
        if result.get("status") == "passed":
            reasons.append("tests passed")
    for result in test_errors:
        summary = str(result.get("summary", "")).strip()
        if "dependencies missing" in summary.lower():
            reasons.append("tests could not run: dependencies missing")
        elif summary:
            reasons.append(f"tests could not run: {summary}")
        else:
            reasons.append("tests could not run")

    if highest_code == "high":
        reasons.append("high-severity code finding")
    for finding in security_findings:
        severity = finding.get("severity", "low")
        if severity in {"high", "critical"}:
            package_name = finding.get("package_name", "unknown")
            reasons.append(f"{severity}-severity security finding in {package_name}")

    if not reasons:
        reasons.append("no blocking code or security findings")

    if highest_security == "critical" or failed_tests:
        verdict = "BLOCK"
        confidence = 0.9
    elif highest_code == "high" or highest_security == "high":
        verdict = "MERGE_WITH_COMMENTS"
        confidence = 0.8
    else:
        verdict = "MERGE"
        confidence = 0.72

    if test_errors or injection_flags:
        confidence = min(confidence, 0.55)

    return {"verdict": verdict, "confidence": confidence, "reasons": reasons}


def should_request_human_approval(verdict: str, confidence: float) -> bool:
    if verdict == "BLOCK":
        return True
    if confidence < LOW_CONFIDENCE_THRESHOLD:
        return True
    return False


def orchestrator_node(state: MergeGuardState) -> dict[str, Any]:
    if state.get("review_status") == "escalated":
        return {
            "review_status": "escalated",
            "requires_human_approval": True,
            "human_approved": None,
        }

    result = combine_verdict(
        code_findings=[item.model_dump() for item in state.get("code_findings", [])],
        test_results=state.get("test_results", []),
        security_findings=[item.model_dump() for item in state.get("security_findings", [])],
        injection_flags=state.get("injection_flags", []),
    )
    requires_approval = should_request_human_approval(result["verdict"], result["confidence"])
    return {
        **result,
        "requires_human_approval": requires_approval,
        "human_approved": None if requires_approval else True,
        "review_status": "ready_for_human_review" if requires_approval else "auto_approved",
    }


def human_review_node(state: MergeGuardState) -> dict[str, Any]:
    if state.get("review_status") == "escalated":
        return {}

    if state.get("no_human") and state.get("requires_human_approval", False):
        return {
            "review_status": "evaluation_no_human",
            "final_verdict": state.get("verdict"),
            "human_override": False,
            "override_reason": None,
        }

    if not state.get("requires_human_approval", False):
        return {
            "review_status": "auto_approved",
            "human_approved": True,
            "final_verdict": state.get("verdict"),
            "human_override": False,
            "override_reason": None,
        }

    review = interrupt(
        {
            "verdict": state.get("verdict"),
            "confidence": state.get("confidence"),
            "reasons": state.get("reasons", []),
            "findings": {
                "code": [item.model_dump() for item in state.get("code_findings", [])],
                "security": [item.model_dump() for item in state.get("security_findings", [])],
            },
        }
    )
    if not isinstance(review, dict):
        raise ValueError("Human review response must contain a decision and reason.")
    decision = review.get("decision")
    reason = str(review.get("reason", "")).strip()
    if decision not in {"MERGE", "MERGE_WITH_COMMENTS", "BLOCK"}:
        raise ValueError("Human review decision is not allowed.")
    is_override = decision != state.get("verdict")
    if is_override and not reason:
        raise ValueError("A reason is required when overriding the automated verdict.")
    return {
        "review_status": "human_reviewed",
        "human_approved": True,
        "final_verdict": decision,
        "human_override": is_override,
        "override_reason": reason or None,
    }


def build_graph():
    graph = StateGraph(MergeGuardState)
    retry_policy = RetryPolicy(
        max_attempts=3,
        initial_interval=0.1,
        backoff_factor=2.0,
        max_interval=1.0,
        retry_on=lambda error: True,
    )
    graph.add_node("code_analysis", code_analysis_node, retry_policy=retry_policy)
    graph.add_node("test_execution", test_execution_node, retry_policy=retry_policy)
    graph.add_node("security_review", security_review_node, retry_policy=retry_policy)
    graph.add_node("orchestrator", orchestrator_node)
    graph.add_node("human_review", human_review_node)
    graph.add_edge(START, "code_analysis")
    graph.add_edge(START, "test_execution")
    graph.add_edge(START, "security_review")
    graph.add_edge(["code_analysis", "test_execution", "security_review"], "orchestrator")
    graph.add_edge("orchestrator", "human_review")
    graph.add_edge("human_review", END)
    return graph
