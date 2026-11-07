"""Hand-label workflow for risk flags: export a sheet, label it yourself, score the rules against it."""
from __future__ import annotations

from collections import Counter

import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score

from ..risk import RULES, risk_matches


def make_label_sheet(df: pd.DataFrame, out_csv: str, n: int = 250, seed: int = 0) -> pd.DataFrame:
    s = df.sample(n=min(n, len(df)), random_state=seed)[["complaint_id", "narrative"]].copy()
    s["narrative"] = s["narrative"].str.slice(0, 1200)
    s["risk_flag"] = ""  # you fill: 1 = needs compliance/regulatory attention, 0 = routine
    s["severity"] = ""   # you fill: low / medium / high
    s["notes"] = ""
    s.to_csv(out_csv, index=False)
    return s


def score_rules(sheet_csv: str) -> dict:
    s = pd.read_csv(sheet_csv, dtype={"risk_flag": str})
    required = {"narrative", "risk_flag"}
    missing = required - set(s.columns)
    if missing:
        raise ValueError(f"label sheet is missing required columns: {sorted(missing)}")
    s = s[s["risk_flag"].isin(["0", "1"])].copy()
    if s.empty:
        raise ValueError("no labelled rows: fill the risk_flag column with 0/1 first")
    y = s["risk_flag"].astype(int).to_numpy()
    matches = s["narrative"].fillna("").astype(str).map(risk_matches)
    pred = matches.map(bool).astype(int).to_numpy()
    tp = int(((pred == 1) & (y == 1)).sum())
    fp = int(((pred == 1) & (y == 0)).sum())
    fn = int(((pred == 0) & (y == 1)).sum())
    prec, rec = tp / max(tp + fp, 1), tp / max(tp + fn, 1)
    per_rule = {}
    for rule in RULES:
        rule_pred = matches.map(lambda row: int(rule in row)).to_numpy()
        per_rule[rule] = {
            "support": int(rule_pred.sum()),
            "precision": round(float(precision_score(y, rule_pred, zero_division=0)), 3),
            "recall": round(float(recall_score(y, rule_pred, zero_division=0)), 3),
            "f1": round(float(f1_score(y, rule_pred, zero_division=0)), 3),
        }

    severity_metrics = {}
    if "severity" in s:
        severity = s["severity"].fillna("").astype(str).str.strip().str.lower()
        for level in ("high", "medium", "low"):
            subset = severity.eq(level).to_numpy()
            positives = subset & (y == 1)
            severity_metrics[level] = {
                "labelled": int(subset.sum()),
                "risk_positives": int(positives.sum()),
                "rule_flagged": int((pred[subset] == 1).sum()),
                "rule_recall": round(float(pred[positives].mean()), 3) if positives.any() else None,
            }

    return {
        "n_labelled": len(s),
        "positives": int(y.sum()),
        "precision": round(float(prec), 3),
        "recall": round(float(rec), 3),
        "f1": round(float(2 * prec * rec / max(prec + rec, 1e-9)), 3),
        "accuracy": round(float(accuracy_score(y, pred)), 3),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "per_rule": per_rule,
        "severity": severity_metrics,
        "evaluation_note": "Rule metrics are measured only on rows with hand-entered risk_flag labels.",
    }


def audit_rule_coverage(df: pd.DataFrame, manifest: dict) -> dict:
    """Describe rule coverage on an unlabeled held-out dataset; this is not a quality score."""
    matches = df["narrative"].fillna("").astype(str).map(risk_matches)
    counts = Counter(rule for row in matches for rule in row)
    flagged_rows = int(matches.map(bool).sum())
    by_product = {}
    for product, indices in df.groupby("product", dropna=False).groups.items():
        product_matches = matches.loc[indices]
        n = len(product_matches)
        by_product[str(product)] = {
            "rows": n,
            "flagged_rows": int(product_matches.map(bool).sum()),
            "flagged_rate": round(float(product_matches.map(bool).mean()), 4),
        }

    return {
        "evaluation_type": "unlabeled_rule_coverage",
        "evaluation_note": (
            "Coverage describes how often rules trigger. Without hand labels it does not measure "
            "precision, recall, correctness, or calibrated priority."
        ),
        "data_source": manifest.get("data_source"),
        "data_source_type": manifest.get("data_source_type", "unspecified"),
        "label_col": manifest["label_col"],
        "n_train": int(manifest["n_train"]),
        "n_test": len(df),
        "test_start": manifest.get("temporal_split", {}).get("test_start"),
        "test_end": str(df["date_received"].max().date()),
        "flagged_rows": flagged_rows,
        "flagged_rate": round(flagged_rows / max(len(df), 1), 4),
        "rows_by_rule": {
            rule: {"rows": counts[rule], "rate": round(counts[rule] / max(len(df), 1), 4)}
            for rule in RULES
        },
        "rows_by_flag_count": {
            str(count): amount
            for count, amount in sorted(Counter(matches.map(len)).items())
        },
        "by_product": by_product,
    }


def coverage_to_markdown(report: dict) -> str:
    lines = [
        "# Risk-rule coverage audit",
        "",
        report["evaluation_note"],
        "",
        f"Source: `{report['data_source']}` ({report['data_source_type']}). "
        f"Temporal holdout: {report['n_test']:,} rows, "
        f"{report['test_start']} to {report['test_end']}.",
        f"Rules flagged {report['flagged_rows']:,} rows "
        f"({report['flagged_rate']:.1%}).",
        "",
        "## Trigger coverage by rule",
        "",
        "| Rule | Rows | Holdout rate |",
        "|---|---:|---:|",
    ]
    lines.extend(
        f"| {rule} | {values['rows']:,} | {values['rate']:.1%} |"
        for rule, values in report["rows_by_rule"].items()
    )
    lines.extend([
        "",
        "## Trigger coverage by product",
        "",
        "| Product | Rows | Flagged | Flagged rate |",
        "|---|---:|---:|---:|",
    ])
    lines.extend(
        f"| {product} | {values['rows']:,} | {values['flagged_rows']:,} | "
        f"{values['flagged_rate']:.1%} |"
        for product, values in report["by_product"].items()
    )
    lines.extend([
        "",
        "## Priority and validation gaps",
        "",
        "* The current rules return categories, not an ordered or calibrated priority score.",
        "* These unlabeled coverage counts cannot establish whether a flagged complaint is high priority.",
        "* Hand-label representative temporal-holdout rows with `risk_flag` and severity, then run "
        "`eval-risk` to measure overall and per-rule performance.",
    ])
    return "\n".join(lines) + "\n"


def score_to_markdown(report: dict) -> str:
    lines = [
        "# Hand-labeled risk-rule evaluation",
        "",
        report["evaluation_note"],
        "",
        f"* Labeled rows: {report['n_labelled']:,}; positive rows: {report['positives']:,}",
        f"* Precision: {report['precision']}; recall: {report['recall']}; "
        f"F1: {report['f1']}; accuracy: {report['accuracy']}",
        f"* Confusion counts: TP {report['tp']}, FP {report['fp']}, FN {report['fn']}",
        "",
        "## Per-rule metrics",
        "",
        "| Rule | Triggered rows | Precision | Recall | F1 |",
        "|---|---:|---:|---:|---:|",
    ]
    lines.extend(
        f"| {rule} | {values['support']:,} | {values['precision']} | "
        f"{values['recall']} | {values['f1']} |"
        for rule, values in report["per_rule"].items()
    )
    if report["severity"]:
        lines.extend([
            "",
            "## Severity breakdown",
            "",
            "| Severity | Labeled | Risk positives | Rule flagged | Recall on positives |",
            "|---|---:|---:|---:|---:|",
        ])
        lines.extend(
            f"| {level} | {values['labelled']:,} | {values['risk_positives']:,} | "
            f"{values['rule_flagged']:,} | {values['rule_recall']} |"
            for level, values in report["severity"].items()
        )
    return "\n".join(lines) + "\n"
