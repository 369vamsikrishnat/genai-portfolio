from mergeguard.workflow.graph import SecurityFinding, build_graph, combine_verdict


def test_security_finding_model():
    finding = SecurityFinding(
        severity="critical",
        description="Potential dependency vulnerability in requests package",
        package_name="requests",
    )

    assert finding.severity == "critical"
    assert finding.package_name == "requests"


def test_combine_verdict_blocks_on_critical_security():
    verdict = combine_verdict(
        code_findings=[{"severity": "medium", "description": "logic risk"}],
        test_results=[{"status": "failed", "summary": "tests failed"}],
        security_findings=[{"severity": "critical", "description": "critical issue", "package_name": "requests"}],
    )

    assert verdict["verdict"] == "BLOCK"
    assert verdict["confidence"] >= 0.8


def test_build_graph_contains_security_node_and_orchestrator():
    graph = build_graph()
    assert "security_review" in graph.nodes
    assert "orchestrator" in graph.nodes
