"""Data-quality report for the joined dataset (pandas; run on a sample for big data)."""
from __future__ import annotations

import re
from datetime import date

import pandas as pd

from .pii import PATTERNS

_PII_RX = {n: re.compile(p) for n, p, _ in PATTERNS}
_TOKENS = ("[SSN]", "[CARD]", "[EMAIL]", "[PHONE]", "[NUMBER]")


def pii_scan(narratives: pd.Series) -> dict:
    """Rows that STILL match a PII pattern after redaction (should be ~0), plus mask-token usage."""
    s = narratives.fillna("").astype(str)
    leaks = {n: int(s.str.contains(rx).sum()) for n, rx in _PII_RX.items()}
    return {"rows_scanned": len(s), "still_matching": leaks,
            "rows_with_redaction_tokens": int(s.apply(lambda t: any(k in t for k in _TOKENS)).sum()),
            "rows_with_cfpb_xxxx_mask": int(s.str.contains("XXXX", regex=False).sum())}


def normalized_hash_series(narratives: pd.Series) -> pd.Series:
    import hashlib

    norm = narratives.fillna("").str.lower().str.replace(r"[^a-z]+", " ", regex=True).str.strip()
    return norm.map(lambda t: hashlib.md5(t.encode()).hexdigest())


def build_report(df: pd.DataFrame, totals: dict | None = None, sample_note: str = "") -> dict:
    h = df["narrative_hash"] if "narrative_hash" in df.columns else normalized_hash_series(df["narrative"])
    length = df["narrative"].fillna("").str.len()
    top_products = df["product"].value_counts(normalize=True).head(10).round(4).to_dict()
    dup_share = 1 - h.nunique() / max(len(df), 1)
    by_year = df.groupby(df["date_received"].dt.year).size().to_dict()
    return {
        "generated": date.today().isoformat(), "sample_note": sample_note, "rows": len(df),
        "date_min": str(df["date_received"].min().date()), "date_max": str(df["date_received"].max().date()),
        "duplicate_complaint_ids": int(df["complaint_id"].duplicated().sum()),
        "template_duplicate_share": round(float(dup_share), 4),
        "distinct_narratives": int(h.nunique()),
        "narrative_chars": {f"p{q}": int(length.quantile(q / 100)) for q in (5, 50, 95, 99)},
        "short_narratives_lt_50_chars": int((length < 50).sum()),
        "missing_share": {c: round(float(df[c].isna().mean()), 4)
                          for c in ("product", "issue", "company", "company_response") if c in df.columns},
        "n_products": int(df["product"].nunique()), "n_issues": int(df["issue"].nunique()),
        "top_products": top_products, "rows_by_year": {int(k): int(v) for k, v in by_year.items()},
        "pii": pii_scan(df["narrative"]), "totals_from_full_data": totals or {},
    }


def to_markdown(r: dict) -> str:
    L = ["# Data-quality report", "", f"Generated {r['generated']}. {r['sample_note']}", "",
         f"* Rows analysed: **{r['rows']:,}**; dates {r['date_min']} to {r['date_max']}",
         f"* Duplicate complaint IDs: **{r['duplicate_complaint_ids']}** (must be 0)",
         f"* Template duplication: **{r['template_duplicate_share']:.1%}** of narratives repeat another narrative "
         f"({r['distinct_narratives']:,} distinct). Index/eval de-duplicate these so retrieval is not rewarded for "
         "finding its own template twin.",
         f"* Narrative length (chars): {r['narrative_chars']}; under 50 chars: {r['short_narratives_lt_50_chars']:,}",
         f"* Missing share: {r['missing_share']}",
         f"* Products: {r['n_products']}, issues: {r['n_issues']}", "", "## Top products", ""]
    L += [f"* {k}: {v:.1%}" for k, v in r["top_products"].items()]
    L += ["", "## Rows by year", ""] + [f"* {k}: {v:,}" for k, v in r["rows_by_year"].items()]
    p = r["pii"]
    L += ["", "## PII check (after redaction)", "",
          f"* Rows still matching a PII pattern: {p['still_matching']} (target: all 0)",
          f"* Rows containing our redaction tokens: {p['rows_with_redaction_tokens']:,}; "
          f"CFPB's own XXXX mask: {p['rows_with_cfpb_xxxx_mask']:,}",
          "* Regexes cannot catch names/addresses in free text. Spot-read 100 random rows before publishing anything."]
    if r["totals_from_full_data"]:
        L += ["", "## Join coverage (from ingest)", ""] + [f"* {k}: {v}" for k, v in r["totals_from_full_data"].items()]
    return "\n".join(L) + "\n"