from __future__ import annotations

import argparse
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from mergeguard.evaluation.scoring import (
    VERDICT_LABELS,
    compute_accuracy,
    confusion_matrix,
    per_class_precision_recall,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _run_real_pipeline(pr: dict[str, Any]) -> dict[str, Any]:
    from mergeguard.worker.main import process_job

    results: list[dict[str, Any]] = []
    job_id = str(uuid.uuid4())
    succeeded = process_job(
        {
            "job_id": job_id,
            "owner": pr["owner"],
            "repo": pr["repo"],
            "pr_number": pr["pr_number"],
        },
        no_human=True,
        result_callback=results.append,
    )
    if not succeeded or not results:
        return {"status": "failed", "predicted_verdict": None}

    result = results[0]
    verdict = result.get("final_verdict") or result.get("verdict")
    return {
        "status": "completed",
        "review_status": result.get("review_status"),
        "predicted_verdict": verdict,
    }


def run_golden_evaluation(
    golden_prs: list[dict[str, Any]],
    pipeline_runner: Callable[[dict[str, Any]], str | dict[str, Any]] | None = None,
) -> dict[str, Any]:
    runner = pipeline_runner or _run_real_pipeline
    per_pr_results: list[dict[str, Any]] = []
    predictions: dict[str, str | None] = {}
    expected: dict[str, str] = {}

    for pr in golden_prs:
        pr_id = f"{pr['owner']}/{pr['repo']}#{pr['pr_number']}"
        pipeline_result: str | dict[str, Any] | None = None
        try:
            pipeline_result = runner(pr)
            if isinstance(pipeline_result, str):
                predicted = pipeline_result
                status = "completed"
            else:
                predicted = pipeline_result.get("predicted_verdict") or pipeline_result.get("final_verdict") or pipeline_result.get("verdict")
                status = str(pipeline_result.get("status", "completed"))
        except Exception as error:
            predicted = None
            status = f"error: {type(error).__name__}"

        predictions[pr_id] = predicted
        expected[pr_id] = pr["expected_verdict"]
        per_pr_results.append(
            {
                "owner": pr["owner"],
                "repo": pr["repo"],
                "pr_number": pr["pr_number"],
                "expected_verdict": pr["expected_verdict"],
                "predicted_verdict": predicted,
                "status": status,
                "review_status": pipeline_result.get("review_status") if isinstance(pipeline_result, dict) else None,
                "rationale": pr["rationale"],
            }
        )

    return {
        "accuracy": compute_accuracy(predictions, expected),
        "per_class_precision_recall": per_class_precision_recall(predictions, expected),
        "confusion_matrix": confusion_matrix(predictions, expected),
        "labels": list(VERDICT_LABELS),
        "total_prs": len(golden_prs),
        "results": per_pr_results,
    }


def _validate_golden_prs(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise ValueError("Golden PR set must be a JSON array.")
    required = {"owner", "repo", "pr_number", "expected_verdict", "rationale"}
    validated = []
    for index, item in enumerate(value):
        if not isinstance(item, dict) or not required.issubset(item):
            raise ValueError(f"Golden PR entry {index} must contain {', '.join(sorted(required))}.")
        if item["expected_verdict"] not in VERDICT_LABELS:
            raise ValueError(f"Golden PR entry {index} has an invalid expected_verdict.")
        if not isinstance(item["pr_number"], int) or item["pr_number"] < 1:
            raise ValueError(f"Golden PR entry {index} has an invalid pr_number.")
        validated.append(item)
    return validated


def _print_summary(report: dict[str, Any]) -> None:
    print(f"Golden PR accuracy: {report['accuracy'] if report['accuracy'] is not None else 'n/a'}")
    print(f"Evaluated PRs: {report['total_prs']}")
    print("\nPer-PR results")
    print(f"{'PR':<36} {'EXPECTED':<22} {'PREDICTED':<22} {'STATUS'}")
    for item in report["results"]:
        pr_name = f"{item['owner']}/{item['repo']}#{item['pr_number']}"
        print(
            f"{pr_name:<36} {item['expected_verdict']:<22} "
            f"{str(item['predicted_verdict'] or 'n/a'):<22} {item['status']}"
        )
    print("\nPer-class precision / recall")
    print(f"{'VERDICT':<24} {'PRECISION':<12} {'RECALL':<12}")
    for label, metrics in report["per_class_precision_recall"].items():
        precision = metrics["precision"] if metrics["precision"] is not None else "n/a"
        recall = metrics["recall"] if metrics["recall"] is not None else "n/a"
        print(f"{label:<24} {str(precision):<12} {str(recall):<12}")
    print("\nConfusion matrix (rows: expected, columns: predicted)")
    labels = report["labels"]
    print(f"{'EXPECTED':<24}" + "".join(f"{label:<22}" for label in labels))
    for expected_label in labels:
        counts = report["confusion_matrix"][expected_label]
        print(f"{expected_label:<24}" + "".join(f"{counts[label]:<22}" for label in labels))


def main(
    argv: list[str] | None = None,
    *,
    pipeline_runner: Callable[[dict[str, Any]], str | dict[str, Any]] | None = None,
) -> Path:
    parser = argparse.ArgumentParser(description="Run the human-labeled golden PR evaluation set.")
    parser.add_argument("--golden-set", type=Path, default=PROJECT_ROOT / "eval" / "golden_prs.json")
    parser.add_argument("--results-dir", type=Path, default=PROJECT_ROOT / "eval" / "results")
    parser.add_argument(
        "--no-human",
        action="store_true",
        required=True,
        help="Record automated verdicts without pausing for human approval.",
    )
    arguments = parser.parse_args(argv)

    golden_prs = _validate_golden_prs(json.loads(arguments.golden_set.read_text(encoding="utf-8")))
    report = run_golden_evaluation(golden_prs, pipeline_runner=pipeline_runner)
    report["generated_at"] = datetime.now(timezone.utc).isoformat()

    arguments.results_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    output_path = arguments.results_dir / f"{timestamp}.json"
    output_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    _print_summary(report)
    print(f"\nResults written to {output_path}")
    return output_path


if __name__ == "__main__":
    main()