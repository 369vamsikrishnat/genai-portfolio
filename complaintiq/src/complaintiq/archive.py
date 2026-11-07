"""Helpers for the CFPB narratives archive (FOIA Reading Room zips of CSVs).

The archive's schema is detected from the real header (never assumed): use `inspect-archive` first.
"""
from __future__ import annotations

import re
import shutil
import zipfile
from pathlib import Path

import pandas as pd

ID_CANDIDATES = ["Complaint ID", "complaint_id", "complaintid", "ID"]
NARR_CANDIDATES = ["Consumer complaint narrative", "complaint_what_happened", "narrative",
                   "consumercomplaintnarrative", "Complaint narrative"]


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def find_column(header: list[str], candidates: list[str], what: str) -> str:
    by_norm = {_norm(h): h for h in header}
    for c in candidates:
        if _norm(c) in by_norm:
            return by_norm[_norm(c)]
    raise ValueError(f"cannot find the {what} column. Header was: {header}. "
                     f"Run `python -m complaintiq inspect-archive --path <file>` and tell me what it shows.")


def expand_inputs(paths: list[str | Path]) -> list[Path]:
    """Files stay as-is; directories expand to their .zip/.csv files (sorted)."""
    out: list[Path] = []
    for p in map(Path, paths):
        if p.is_dir():
            out += sorted([*p.rglob("*.zip"), *p.rglob("*.csv")])
        elif p.exists():
            out.append(p)
        else:
            raise FileNotFoundError(p)
    if not out:
        raise FileNotFoundError("no .zip/.csv files found in the given archive paths")
    return out


def extract_all_csv(zip_path: Path, out_dir: Path) -> list[Path]:
    """Stream every CSV member of a zip to disk (skips members already extracted at full size)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    out = []
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            if not info.filename.lower().endswith(".csv"):
                continue
            target = out_dir / f"{zip_path.stem}__{Path(info.filename).name}"
            if not (target.exists() and target.stat().st_size == info.file_size):
                tmp = target.with_suffix(".part")
                with zf.open(info) as src, open(tmp, "wb") as dst:
                    shutil.copyfileobj(src, dst, 1 << 20)
                tmp.replace(target)
            out.append(target)
    if not out:
        raise ValueError(f"no .csv inside {zip_path}")
    return out


def inspect(path: str | Path, rows: int = 2) -> dict:
    """Header + a couple of sample rows (narratives truncated) for a zip or csv. Reads almost nothing."""
    p = Path(path)
    info: dict = {"path": str(p), "size_mb": round(p.stat().st_size / 2**20, 1)}
    if p.suffix.lower() == ".zip":
        with zipfile.ZipFile(p) as zf:
            members = [i for i in zf.infolist() if i.filename.lower().endswith(".csv")]
            info["members"] = [{"name": i.filename, "size_mb": round(i.file_size / 2**20, 1)} for i in members]
            if not members:
                raise ValueError("zip contains no CSV files")
            with zf.open(members[0]) as f:
                df = pd.read_csv(f, nrows=rows, dtype=str)
    else:
        df = pd.read_csv(p, nrows=rows, dtype=str)
    info["columns"] = list(df.columns)
    try:
        info["id_column"] = find_column(list(df.columns), ID_CANDIDATES, "complaint id")
    except ValueError:
        info["id_column"] = None
    try:
        info["narrative_column"] = find_column(list(df.columns), NARR_CANDIDATES, "narrative")
    except ValueError:
        info["narrative_column"] = None
    sample = df.head(rows).copy()
    for c in sample.columns:
        sample[c] = sample[c].astype(str).str.slice(0, 120)
    info["sample"] = sample.to_dict("records")
    return info