"""Streaming ingest: CFPB zip -> redacted, deduped Parquet partitioned by year/month (DuckDB).

Idempotent: the source file's SHA-256 is recorded in a SQLite checkpoint table. Re-running on
the same file with the same options is a no-op; a new file replaces the output atomically.
NOTE: requires `pip install .[data]` (duckdb, pyarrow).
"""
from __future__ import annotations

import hashlib
import shutil
import sqlite3
import time
import zipfile
from pathlib import Path

import requests

from .pii import sql_redact_expr

CFPB_URL = "https://files.consumerfinance.gov/ccdb/complaints.csv.zip"


def download(dest_dir: str | Path, url: str = CFPB_URL) -> Path:
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    out = dest_dir / "complaints.csv.zip"
    tmp = out.with_suffix(".part")
    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
    tmp.replace(out)
    return out


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while block := f.read(chunk):
            h.update(block)
    return h.hexdigest()


def extract_csv(zip_path: Path, out_dir: Path) -> Path:
    """Stream the first CSV member to disk (never loads it into memory)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as zf:
        names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
        if not names:
            raise ValueError(f"no .csv inside {zip_path}")
        info = zf.getinfo(names[0])
        target = out_dir / Path(names[0]).name
        if target.exists() and target.stat().st_size == info.file_size:
            return target
        tmp = target.with_suffix(".part")
        with zf.open(names[0]) as src, open(tmp, "wb") as dst:
            shutil.copyfileobj(src, dst, 1 << 20)
        tmp.replace(target)
    return target


def _checkpoints(out_dir: Path) -> sqlite3.Connection:
    con = sqlite3.connect(out_dir / "_checkpoints.db")
    con.execute("CREATE TABLE IF NOT EXISTS loads(source_sha TEXT, opts TEXT, rows INTEGER, "
                "loaded_at TEXT, PRIMARY KEY(source_sha, opts))")
    return con


def ingest(src: str | Path, out_dir: str | Path, since_year: int | None = None,
           keep_without_narrative: bool = False, memory_limit: str = "4GB") -> dict:
    import duckdb

    src, out_dir = Path(src), Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv = extract_csv(src, out_dir / "_csv") if src.suffix.lower() == ".zip" else src
    sha = sha256_file(csv)
    opts = f"since={since_year};narr_only={not keep_without_narrative}"
    final, tmp = out_dir / "complaints", out_dir / "complaints.tmp"

    ck = _checkpoints(out_dir)
    row = ck.execute("SELECT rows FROM loads WHERE source_sha=? AND opts=?", (sha, opts)).fetchone()
    if row and final.exists():
        return {"skipped": True, "rows": row[0], "sha256": sha}

    q = lambda s: s.replace("'", "''")  # noqa: E731
    date_expr = ("COALESCE(try_cast(\"Date received\" AS DATE), "
                 "CAST(try_strptime(\"Date received\", '%m/%d/%Y') AS DATE), "
                 "CAST(try_strptime(\"Date received\", '%m/%d/%y') AS DATE))")
    filters = ["complaint_id IS NOT NULL", "date_received IS NOT NULL"]
    if not keep_without_narrative:
        filters.append("narrative IS NOT NULL AND length(trim(narrative)) > 0")
    if since_year:
        filters.append(f"year(date_received) >= {int(since_year)}")
    sql = f"""
    COPY (
      WITH raw AS (
        SELECT try_cast("Complaint ID" AS BIGINT) AS complaint_id,
               {date_expr} AS date_received,
               "Product" AS product, "Sub-product" AS sub_product, "Issue" AS issue,
               "Sub-issue" AS sub_issue, "Company" AS company, "State" AS state,
               "ZIP code" AS zip3, "Submitted via" AS submitted_via,
               "Company response to consumer" AS company_response,
               "Timely response?" AS timely, "Consumer disputed?" AS disputed,
               {sql_redact_expr('"Consumer complaint narrative"')} AS narrative
        FROM read_csv('{q(str(csv))}', header=true, all_varchar=true, ignore_errors=true)
      )
      SELECT *, year(date_received) AS year, month(date_received) AS month
      FROM raw WHERE {' AND '.join(filters)}
      QUALIFY row_number() OVER (PARTITION BY complaint_id ORDER BY date_received DESC) = 1
    ) TO '{q(str(tmp))}' (FORMAT PARQUET, PARTITION_BY (year, month), COMPRESSION zstd, OVERWRITE_OR_IGNORE true)
    """
    shutil.rmtree(tmp, ignore_errors=True)
    t0 = time.time()
    con = duckdb.connect()
    con.execute(f"SET memory_limit='{memory_limit}'")
    con.execute(f"SET temp_directory='{q(str(out_dir / '_spill'))}'")
    con.execute(sql)
    shutil.rmtree(final, ignore_errors=True)
    tmp.rename(final)
    n = con.execute(f"SELECT count(*) FROM read_parquet('{q(str(final))}/**/*.parquet', hive_partitioning=true)").fetchone()[0]
    ck.execute("INSERT OR REPLACE INTO loads VALUES (?,?,?,datetime('now'))", (sha, opts, n))
    ck.commit()
    return {"skipped": False, "rows": n, "sha256": sha, "seconds": round(time.time() - t0, 1)}
