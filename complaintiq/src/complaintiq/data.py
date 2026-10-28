"""Load complaints from partitioned Parquet (DuckDB) or from a CSV (pandas)."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from .schema import COLUMN_MAP

CORE_COLS = ["complaint_id", "date_received", "product", "issue", "company", "narrative"]


def _standardize(df: pd.DataFrame) -> pd.DataFrame:
    df = df.rename(columns={k: v for k, v in COLUMN_MAP.items() if k in df.columns})
    missing = [c for c in CORE_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"missing required columns: {missing}")
    df["date_received"] = pd.to_datetime(df["date_received"], errors="coerce")
    df = df.dropna(subset=["date_received", "complaint_id"])
    df["complaint_id"] = df["complaint_id"].astype("int64")
    return df.drop_duplicates("complaint_id")


def _has_text(s: pd.Series) -> pd.Series:
    return s.notna() & s.astype(str).str.strip().ne("")


def load_complaints(path: str | Path, since_year: int | None = None, until_year: int | None = None,
                    only_narrative: bool = True, limit: int | None = None, seed: int = 0) -> pd.DataFrame:
    p = Path(path)
    if p.suffix.lower() in (".csv", ".gz"):
        df = _standardize(pd.read_csv(p, dtype=str, keep_default_na=False, na_values=[""]))
        if only_narrative:
            df = df[_has_text(df["narrative"])]
        if since_year:
            df = df[df["date_received"].dt.year >= since_year]
        if until_year:
            df = df[df["date_received"].dt.year <= until_year]
        if limit and len(df) > limit:
            df = df.sample(n=limit, random_state=seed)
    else:
        import duckdb  # lazy: only needed for the real-data path

        glob = str(p / "**" / "*.parquet").replace("'", "''")
        where = ["1=1"]
        if only_narrative:
            where.append("narrative IS NOT NULL AND length(trim(narrative)) > 0")
        if since_year:
            where.append(f"year >= {int(since_year)}")
        if until_year:
            where.append(f"year <= {int(until_year)}")
        order = f"ORDER BY hash(CAST(complaint_id AS VARCHAR) || '-{int(seed)}') LIMIT {int(limit)}" if limit else ""
        sql = (f"SELECT * FROM read_parquet('{glob}', hive_partitioning=true) "
               f"WHERE {' AND '.join(where)} {order}")
        df = _standardize(duckdb.connect().execute(sql).df())
    return df.reset_index(drop=True)
