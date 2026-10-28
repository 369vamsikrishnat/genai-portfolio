"""Hand-label workflow for risk flags: export a sheet, label it yourself, score the rules against it."""
from __future__ import annotations

import pandas as pd

from ..risk import risk_flags


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
    s = s[s["risk_flag"].isin(["0", "1"])].copy()
    if s.empty:
        raise ValueError("no labelled rows: fill the risk_flag column with 0/1 first")
    y = s["risk_flag"].astype(int).to_numpy()
    pred = s["narrative"].map(lambda t: int(bool(risk_flags(str(t))))).to_numpy()
    tp = int(((pred == 1) & (y == 1)).sum())
    fp = int(((pred == 1) & (y == 0)).sum())
    fn = int(((pred == 0) & (y == 1)).sum())
    prec, rec = tp / max(tp + fp, 1), tp / max(tp + fn, 1)
    return {"n_labelled": len(s), "positives": int(y.sum()), "precision": round(prec, 3),
            "recall": round(rec, 3), "f1": round(2 * prec * rec / max(prec + rec, 1e-9), 3),
            "tp": tp, "fp": fp, "fn": fn}
