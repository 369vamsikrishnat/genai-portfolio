from mergeguard.workflow import graph
from mergeguard.workflow.graph import build_graph, human_review_node, should_request_human_approval


def test_should_request_human_approval_for_block_and_low_confidence():
    assert should_request_human_approval("MERGE", 0.72) is False
    assert should_request_human_approval("MERGE", 0.5) is True
    assert should_request_human_approval("BLOCK", 0.9) is True


def test_human_review_node_records_same_verdict_review(monkeypatch):
    state = {
        "verdict": "BLOCK",
        "confidence": 0.9,
        "requires_human_approval": True,
        "human_approved": None,
    }

    monkeypatch.setattr(graph, "interrupt", lambda payload: {"decision": "BLOCK", "reason": ""})

    result = human_review_node(state)

    assert result["review_status"] == "human_reviewed"
    assert result["final_verdict"] == "BLOCK"
    assert result["human_override"] is False


def test_build_graph_contains_human_review_node():
    graph = build_graph()

    assert "human_review" in graph.nodes
