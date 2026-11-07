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


def _sql_list(paths: list[Path]) -> str:
    return "[" + ", ".join("'" + str(x).replace("'", "''") + "'" for x in paths) + "]"


def ingest(src: str | Path, out_dir: str | Path, since_year: int | None = None,
           keep_without_narrative: bool = False, memory_limit: str = "4GB",
           narratives: list[str | Path] | None = None) -> dict:
    """Main CFPB file (+ optional narratives archive joined on Complaint ID) -> partitioned Parquet.

    Since Aug 14 2026 the live CFPB file has NO narrative column; narratives live in the FOIA archive.
    Pass the archive zips/CSVs (or a folder of them) via `narratives`. Returns coverage statistics.
    """
    import duckdb

    from .archive import ID_CANDIDATES, NARR_CANDIDATES, expand_inputs, extract_all_csv, find_column

    src, out_dir = Path(src), Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv = extract_csv(src, out_dir / "_csv") if src.suffix.lower() == ".zip" else src
    archive_csvs: list[Path] = []
    for p in expand_inputs(list(narratives or [])) if narratives else []:
        archive_csvs += extract_all_csv(p, out_dir / "_archive_csv") if p.suffix.lower() == ".zip" else [p]

    sha = sha256_file(csv)
    arch_fp = hashlib.sha256("|".join(f"{c.name}:{c.stat().st_size}" for c in archive_csvs).encode()).hexdigest()[:16]
    opts = f"since={since_year};narr_only={not keep_without_narrative};archive={arch_fp}"
    final, tmp = out_dir / "complaints", out_dir / "complaints.tmp"
    ck = _checkpoints(out_dir)
    row = ck.execute("SELECT rows FROM loads WHERE source_sha=? AND opts=?", (sha, opts)).fetchone()
    if row and final.exists():
        return {"skipped": True, "rows": row[0], "sha256": sha}

    q = lambda s: s.replace("'", "''")  # noqa: E731
    con = duckdb.connect()
    con.execute(f"SET memory_limit='{memory_limit}'")
    con.execute(f"SET temp_directory='{q(str(out_dir / '_spill'))}'")
    con.execute(f"CREATE TEMP VIEW cfpb_main AS SELECT * FROM read_csv('{q(str(csv))}', header=true, "
                "all_varchar=true, ignore_errors=true)")
    header = [r[0] for r in con.execute("DESCRIBE SELECT * FROM cfpb_main").fetchall()]
    base_required = ["Complaint ID", "Date received", "Product", "Issue", "Company"]
    missing = [c for c in base_required if c not in header]
    if missing:
        raise ValueError(f"main CSV is missing required columns {missing}. Found: {header}")
    has_narr = "Consumer complaint narrative" in header
    if not has_narr and not archive_csvs:
        raise ValueError("this CFPB file has no narrative column (CFPB stopped publishing narratives on "
                         "2026-08-14). Download the FOIA 'Consumer Complaint Database Narratives Archive' and "
                         "pass it with --narratives <zip/csv/folder ...>.")

    def col(name: str, alias: str) -> str:
        return f'"{name}" AS {alias}' if name in header else f"CAST(NULL AS VARCHAR) AS {alias}"

    date_expr = ("COALESCE(try_cast(\"Date received\" AS DATE), "
                 "CAST(try_strptime(\"Date received\", '%m/%d/%Y') AS DATE), "
                 "CAST(try_strptime(\"Date received\", '%m/%d/%y') AS DATE))")
    stats: dict = {}
    if archive_csvs:
        files = _sql_list(archive_csvs)
        a_head = [r[0] for r in con.execute(
            f"DESCRIBE SELECT * FROM read_csv({files}, header=true, all_varchar=true, ignore_errors=true, "
            "union_by_name=true)").fetchall()]
        id_c = find_column(a_head, ID_CANDIDATES, "archive complaint-id")
        nar_c = find_column(a_head, NARR_CANDIDATES, "archive narrative")
        con.execute(f"""CREATE TEMP VIEW narr0 AS
            SELECT try_cast("{id_c}" AS BIGINT) AS complaint_id,
                   {sql_redact_expr(f'"{nar_c}"')} AS narrative
            FROM read_csv({files}, header=true, all_varchar=true, ignore_errors=true, union_by_name=true)
            WHERE try_cast("{id_c}" AS BIGINT) IS NOT NULL AND "{nar_c}" IS NOT NULL
              AND length(trim("{nar_c}")) > 0""")
        con.execute("CREATE TEMP VIEW narr AS SELECT * FROM narr0 QUALIFY "
                    "row_number() OVER (PARTITION BY complaint_id ORDER BY length(narrative) DESC) = 1")
        stats["archive_rows"] = con.execute("SELECT count(*) FROM narr0").fetchone()[0]
        stats["archive_distinct_ids"] = con.execute("SELECT count(*) FROM narr").fetchone()[0]
        stats["archive_unmatched_ids"] = con.execute(
            "SELECT count(*) FROM narr n WHERE NOT EXISTS (SELECT 1 FROM cfpb_main m "
            "WHERE try_cast(m.\"Complaint ID\" AS BIGINT) = n.complaint_id)").fetchone()[0]
        join = ("LEFT" if keep_without_narrative else "INNER")
        source = (f"cfpb_main AS m {join} JOIN narr AS n ON try_cast(m.\"Complaint ID\" AS BIGINT) = n.complaint_id")
        narr_expr = "n.narrative"
    else:
        source = "cfpb_main"
        narr_expr = sql_redact_expr('"Consumer complaint narrative"')
    since_f = f" AND year(date_received) >= {int(since_year)}" if since_year else ""
    stats["main_rows_in_scope"] = con.execute(
        f"SELECT count(*) FROM cfpb_main WHERE {date_expr} IS NOT NULL" +
        (f" AND year({date_expr}) >= {int(since_year)}" if since_year else "")).fetchone()[0]

    filters = ["complaint_id IS NOT NULL", "date_received IS NOT NULL"]
    if not keep_without_narrative:
        filters.append("narrative IS NOT NULL AND length(trim(narrative)) > 0")
    sql = f"""
    COPY (
      WITH raw AS (
        SELECT try_cast("Complaint ID" AS BIGINT) AS complaint_id,
               {date_expr} AS date_received,
               {col("Product", "product")}, {col("Sub-product", "sub_product")}, {col("Issue", "issue")},
               {col("Sub-issue", "sub_issue")}, {col("Company", "company")}, {col("State", "state")},
               {col("ZIP code", "zip3")}, {col("Submitted via", "submitted_via")},
               {col("Company response to consumer", "company_response")},
               {col("Timely response?", "timely")}, {col("Consumer disputed?", "disputed")},
               {narr_expr} AS narrative
        FROM {source}
      )
      SELECT *, md5(trim(lower(regexp_replace(narrative, '[^A-Za-z]+', ' ', 'g')))) AS narrative_hash,
             year(date_received) AS year, month(date_received) AS month
      FROM raw WHERE {' AND '.join(filters)}{since_f}
      QUALIFY row_number() OVER (PARTITION BY complaint_id ORDER BY date_received DESC) = 1
    ) TO '{q(str(tmp))}' (FORMAT PARQUET, PARTITION_BY (year, month), COMPRESSION zstd, OVERWRITE_OR_IGNORE true)
    """
    shutil.rmtree(tmp, ignore_errors=True)
    t0 = time.time()
    con.execute(sql)
    shutil.rmtree(final, ignore_errors=True)
    tmp.rename(final)
    glob = f"read_parquet('{q(str(final))}/**/*.parquet', hive_partitioning=true)"
    n = con.execute(f"SELECT count(*) FROM {glob}").fetchone()[0]
    stats["joined_rows"] = n
    if stats["main_rows_in_scope"]:
        stats["narrative_coverage_of_main"] = round(n / stats["main_rows_in_scope"], 4)
    stats["distinct_narrative_hashes"] = con.execute(f"SELECT count(DISTINCT narrative_hash) FROM {glob}").fetchone()[0]
    ck.execute("INSERT OR REPLACE INTO loads VALUES (?,?,?,datetime('now'))", (sha, opts, n))
    ck.commit()
    return {"skipped": False, "rows": n, "sha256": sha, "seconds": round(time.time() - t0, 1), **stats}