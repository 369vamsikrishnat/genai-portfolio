from mergeguard.workflow import graph
from mergeguard.workflow.graph import human_review_node, should_request_human_approval


def test_merge_auto_approved_when_above_low_confidence_threshold():
    state = {
        "verdict": "MERGE",
        "confidence": 0.72,
        "requires_human_approval": False,
        "human_approved": True,
    }

    result = human_review_node(state)

    assert result["review_status"] == "auto_approved"
    assert result["final_verdict"] == "MERGE"
    assert state["requires_human_approval"] is False
    assert state["verdict"] == "MERGE"


def test_block_verdict_can_be_confirmed_without_override(monkeypatch):
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


def test_low_confidence_merge_can_be_confirmed_without_override(monkeypatch):
    state = {
        "verdict": "MERGE",
        "confidence": 0.5,
        "requires_human_approval": True,
        "human_approved": None,
    }

    monkeypatch.setattr(graph, "interrupt", lambda payload: {"decision": "MERGE", "reason": ""})
    result = human_review_node(state)

    assert should_request_human_approval("MERGE", 0.5) is True
    assert result["review_status"] == "human_reviewed"
    assert result["final_verdict"] == "MERGE"
    assert result["human_override"] is False
