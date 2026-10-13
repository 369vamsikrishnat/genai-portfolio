from __future__ import annotations

VERDICT_LABELS = ("MERGE", "MERGE_WITH_COMMENTS", "BLOCK")


class GoldenPRSet:
    def __init__(self) -> None:
        self.examples: list[dict[str, str]] = []

    def add_example(self, *, pr_id: str, expected_verdict: str, notes: str = "") -> dict[str, str]:
        entry = {
            "pr_id": pr_id,
            "expected_verdict": expected_verdict,
            "notes": notes,
        }
        self.examples.append(entry)
        return entry


def compute_accuracy(predictions: dict[str, str | None], expected: dict[str, str]) -> float | None:
    if not expected:
        return None
    correct = sum(1 for pr_id, verdict in expected.items() if predictions.get(pr_id) == verdict)
    return round((correct / len(expected)) * 100, 2)


def per_class_precision_recall(
    predictions: dict[str, str | None],
    expected: dict[str, str],
    labels: tuple[str, ...] = VERDICT_LABELS,
) -> dict[str, dict[str, float | None]]:
    metrics: dict[str, dict[str, float | None]] = {}
    for label in labels:
        true_positive = sum(
            1 for pr_id, expected_label in expected.items()
            if expected_label == label and predictions.get(pr_id) == label
        )
        predicted_positive = sum(1 for pr_id in expected if predictions.get(pr_id) == label)
        actual_positive = sum(1 for expected_label in expected.values() if expected_label == label)
        precision = round((true_positive / predicted_positive) * 100, 2) if predicted_positive else None
        recall = round((true_positive / actual_positive) * 100, 2) if actual_positive else None
        metrics[label] = {"precision": precision, "recall": recall}
    return metrics


def confusion_matrix(
    predictions: dict[str, str | None],
    expected: dict[str, str],
    labels: tuple[str, ...] = VERDICT_LABELS,
) -> dict[str, dict[str, int]]:
    matrix = {expected_label: {predicted_label: 0 for predicted_label in labels} for expected_label in labels}
    for pr_id, expected_label in expected.items():
        predicted_label = predictions.get(pr_id)
        if expected_label in matrix and predicted_label in matrix[expected_label]:
            matrix[expected_label][predicted_label] += 1
    return matrix


def evaluate_verdict_precision(predictions: dict[str, str], expected: dict[str, str]) -> float | None:
    """Deprecated compatibility alias; this metric is accuracy, not precision."""
    return compute_accuracy(predictions, expected)


__all__ = [
    "GoldenPRSet",
    "VERDICT_LABELS",
    "compute_accuracy",
    "confusion_matrix",
    "evaluate_verdict_precision",
    "per_class_precision_recall",
]
