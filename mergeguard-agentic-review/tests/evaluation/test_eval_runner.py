from __future__ import annotations

import json

from scripts.run_golden_eval import main
from mergeguard.workflow import graph
from mergeguard.evaluation.scoring import (
    compute_accuracy,
    confusion_matrix,
    per_class_precision_recall,
)


def test_accuracy_precision_recall_and_confusion_matrix_math():
    expected = {"a": "MERGE", "b": "BLOCK", "c": "BLOCK", "d": "MERGE_WITH_COMMENTS"}
    predictions = {"a": "MERGE", "b": "MERGE", "c": "BLOCK", "d": "MERGE_WITH_COMMENTS"}

    assert compute_accuracy(predictions, expected) == 75.0
    assert per_class_precision_recall(predictions, expected) == {
        "MERGE": {"precision": 50.0, "recall": 100.0},
        "MERGE_WITH_COMMENTS": {"precision": 100.0, "recall": 100.0},
        "BLOCK": {"precision": 100.0, "recall": 50.0},
    }
    assert confusion_matrix(predictions, expected) == {
        "MERGE": {"MERGE": 1, "MERGE_WITH_COMMENTS": 0, "BLOCK": 0},
        "MERGE_WITH_COMMENTS": {"MERGE": 0, "MERGE_WITH_COMMENTS": 1, "BLOCK": 0},
        "BLOCK": {"MERGE": 1, "MERGE_WITH_COMMENTS": 0, "BLOCK": 1},
    }


def test_cli_runner_writes_timestamped_stubbed_results(tmp_path):
    golden_set = tmp_path / "sample.json"
    golden_set.write_text(
        json.dumps(
            [
                {
                    "owner": "fixture-owner",
                    "repo": "fixture-repo",
                    "pr_number": 1,
                    "expected_verdict": "MERGE",
                    "rationale": "test fixture",
                },
                {
                    "owner": "fixture-owner",
                    "repo": "fixture-repo",
                    "pr_number": 2,
                    "expected_verdict": "BLOCK",
                    "rationale": "test fixture",
                },
            ]
        ),
        encoding="utf-8",
    )

    def stub_pipeline(pr):
        return "MERGE" if pr["pr_number"] == 1 else "MERGE_WITH_COMMENTS"

    output_path = main(
        ["--no-human", "--golden-set", str(golden_set), "--results-dir", str(tmp_path / "results")],
        pipeline_runner=stub_pipeline,
    )
    report = json.loads(output_path.read_text(encoding="utf-8"))

    assert report["total_prs"] == 2
    assert report["accuracy"] == 50.0
    assert report["results"][0]["predicted_verdict"] == "MERGE"
    assert report["results"][1]["expected_verdict"] == "BLOCK"
    assert report["confusion_matrix"]["BLOCK"]["MERGE_WITH_COMMENTS"] == 1


def test_no_human_mode_records_block_without_interrupt(monkeypatch):
    monkeypatch.setattr(graph, "code_analysis_node", lambda state: {"code_findings": []})
    monkeypatch.setattr(graph, "test_execution_node", lambda state: {"test_results": [{"status": "failed"}]})
    monkeypatch.setattr(graph, "security_review_node", lambda state: {"security_findings": []})

    from mergeguard.workflow.graph import build_graph

    result = build_graph().compile().invoke(
        {"job_id": "evaluation-job", "no_human": True},
        config={"recursion_limit": 50},
    )

    assert "__interrupt__" not in result
    assert result["verdict"] == "BLOCK"
    assert result["final_verdict"] == "BLOCK"
    assert result["review_status"] == "evaluation_no_human"