"""Classification quality, confidence and calibration metrics."""
from __future__ import annotations

import numpy as np
from sklearn.metrics import accuracy_score, classification_report, f1_score

THRESHOLDS = [0.0, 0.5, 0.6, 0.7, 0.8, 0.9]


def evaluate_classifier(clf, X: np.ndarray, y: np.ndarray, min_support: int = 50) -> dict:
    pred, conf = clf.predict_with_conf(X)
    y = np.asarray(y).astype(str)
    pred = np.asarray(pred).astype(str)

    rep = classification_report(y, pred, output_dict=True, zero_division=0)
    per_class = {
        k: {
            "precision": round(v["precision"], 4),
            "recall": round(v["recall"], 4),
            "f1": round(v["f1-score"], 4),
            "support": int(v["support"]),
        }
        for k, v in rep.items()
        if k not in ("accuracy", "macro avg", "weighted avg")
    }

    big = [k for k, v in per_class.items() if v["support"] >= min_support]
    correct = pred == y
    curve = []

    for threshold in THRESHOLDS:
        keep = conf >= threshold
        curve.append({
            "threshold": threshold,
            "auto_handled": round(float(keep.mean()), 4),
            "auto_accuracy": round(float(correct[keep].mean()), 4) if keep.any() else None,
        })

    edges = np.linspace(0, 1, 11)
    ece = 0.0
    for lo, hi in zip(edges[:-1], edges[1:], strict=True):
        mask = (conf > lo) & (conf <= hi)
        if mask.any():
            ece += mask.mean() * abs(correct[mask].mean() - conf[mask].mean())

    return {
        "n_test": len(y),
        "n_classes": len(per_class),
        "macro_f1": round(float(f1_score(y, pred, average="macro", zero_division=0)), 4),
        "macro_f1_classes_with_support": round(
            float(np.mean([per_class[k]["f1"] for k in big])), 4
        ) if big else None,
        "min_support": min_support,
        "n_classes_with_support": len(big),
        "weighted_f1": round(float(f1_score(y, pred, average="weighted", zero_division=0)), 4),
        "accuracy": round(float(accuracy_score(y, pred)), 4),
        "ece": round(float(ece), 4),
        "majority_class_accuracy": round(
            float(max(np.mean(y == c) for c in set(y))), 4
        ),
        "confidence_curve": curve,
        "per_class": per_class,
    }


def to_markdown(report: dict, manifest: dict) -> str:
    lines = [
        "# Classifier benchmark (held-out temporal split)",
        "",
        f"Data type: `{manifest.get('data_source_type', 'unspecified')}`.",
        f"Data source: `{manifest.get('data_source', 'not recorded')}`.",
        f"Embedder `{manifest['embedder_arg']}`, trained on the earliest "
        f"{manifest['n_train']:,} rows and tested on the latest "
        f"{report['n_test']:,} rows. Label: `{manifest['label_col']}`.",
        f"Sampled rows: {manifest.get('sample') or manifest['n']:,}; "
        f"rows after deduplication: {manifest['n']:,}.",
        "",
        f"* **Macro-F1:** {report['macro_f1']} across {report['n_classes']} classes",
        f"* **Macro-F1 (support >= {report['min_support']}):** "
        f"{report['macro_f1_classes_with_support']}",
        f"* **Weighted-F1:** {report['weighted_f1']}",
        f"* **Accuracy:** {report['accuracy']} "
        f"(majority baseline: {report['majority_class_accuracy']})",
        f"* **Expected calibration error:** {report['ece']}",
        "",
        "## Confidence threshold",
        "",
        "| Threshold | Auto-handled | Accuracy on auto-handled |",
        "|---:|---:|---:|",
    ]

    lines.extend(
        f"| {row['threshold']} | {row['auto_handled']:.1%} | "
        f"{row['auto_accuracy']} |"
        for row in report["confidence_curve"]
    )

    lines.extend([
        "",
        "## Per-class results",
        "",
        "| Class | Precision | Recall | F1 | Support |",
        "|---|---:|---:|---:|---:|",
    ])

    lines.extend(
        f"| {label} | {values['precision']} | {values['recall']} | "
        f"{values['f1']} | {values['support']} |"
        for label, values in sorted(
            report["per_class"].items(),
            key=lambda item: -item[1]["support"],
        )
    )

    return "\n".join(lines) + "\n"
