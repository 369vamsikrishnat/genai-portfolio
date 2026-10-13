from __future__ import annotations

from threading import Barrier

import pytest

from mergeguard.workflow import graph
from mergeguard.workflow.graph import GRAPH_RECURSION_LIMIT, build_graph
from mergeguard.observability.tracing import should_skip_security_review


def test_parallel_agent_updates_join_before_orchestrator(monkeypatch):
    parallel_gate = Barrier(3)

    def agent_update(update):
        parallel_gate.wait(timeout=3)
        return update

    monkeypatch.setattr(graph, "code_analysis_node", lambda state: agent_update({"code_findings": []}))
    monkeypatch.setattr(
        graph,
        "test_execution_node",
        lambda state: agent_update({"test_results": [{"status": "passed", "summary": "ok"}]}),
    )
    monkeypatch.setattr(
        graph,
        "security_review_node",
        lambda state: agent_update({"security_findings": [], "agents_skipped": ["security_review"]}),
    )

    compiled = build_graph().compile()
    topology = compiled.get_graph()
    edges = {(edge.source, edge.target) for edge in topology.edges}
    agent_names = {"code_analysis", "test_execution", "security_review"}

    assert {("__start__", agent) for agent in agent_names} <= edges
    assert {(agent, "orchestrator") for agent in agent_names} <= edges

    result = compiled.invoke(
        {"changed_files": ["src/app.py"]},
        config={"recursion_limit": GRAPH_RECURSION_LIMIT},
    )

    assert result["code_findings"] == []
    assert result["test_results"][0]["status"] == "passed"
    assert result["security_findings"] == []
    assert result["agents_skipped"] == ["security_review"]


def test_security_review_skips_src_only_change_without_running_analysis(monkeypatch):
    def unexpected_github_client(*args, **kwargs):
        raise AssertionError("security skip must not make GitHub or scanner calls")

    monkeypatch.setattr("mergeguard.agents.security.call_agent_tool", unexpected_github_client)

    update = graph.security_review_node({"changed_files": ["src/app.py"], "pr_diff": "+value = 1"})

    assert update == {"security_findings": [], "agents_skipped": ["security_review"]}


@pytest.mark.parametrize(
    "changed_path",
    [
        "Pipfile",
        "Pipfile.lock",
        "src/Pipfile",
        "web/package-lock.json",
        r"web\package-lock.json",
    ],
)
def test_dependency_file_detection_uses_case_insensitive_basename(changed_path: str):
    assert should_skip_security_review([changed_path]) is False


def test_non_dependency_change_skips_security_review():
    assert should_skip_security_review(["src/app.py"]) is True


def test_agent_retry_policy_retries_three_attempts(monkeypatch):
    attempts = 0

    def flaky_code_analysis(state):
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise TimeoutError("temporary agent timeout")
        return {"code_findings": []}

    monkeypatch.setattr(graph, "code_analysis_node", flaky_code_analysis)
    monkeypatch.setattr(
        graph,
        "security_review_node",
        lambda state: {"security_findings": [], "agents_skipped": ["security_review"]},
    )

    result = build_graph().compile().invoke(
        {
            "changed_files": ["src/app.py"],
            "test_results": [{"status": "passed", "summary": "ok"}],
        },
        config={"recursion_limit": GRAPH_RECURSION_LIMIT},
    )

    assert attempts == 3
    assert result["verdict"] == "MERGE"