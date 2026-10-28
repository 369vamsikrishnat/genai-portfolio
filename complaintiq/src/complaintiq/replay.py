"""Replay history month-by-month as simulated batches (for throughput tests and demos)."""
from __future__ import annotations

import time
from collections.abc import Callable, Iterator

import pandas as pd


def iter_months(df: pd.DataFrame) -> Iterator[tuple[str, pd.DataFrame]]:
    period = df["date_received"].dt.to_period("M")
    for p, g in df.groupby(period, sort=True):
        yield str(p), g


def replay(df: pd.DataFrame, handler: Callable[[pd.DataFrame], None],
           done: set[str] | None = None) -> list[dict]:
    """Run handler per month. Months in `done` are skipped (checkpoint/resume)."""
    stats = []
    for month, batch in iter_months(df):
        if done and month in done:
            continue
        t0 = time.perf_counter()
        handler(batch)
        dt = time.perf_counter() - t0
        stats.append({"month": month, "rows": len(batch), "seconds": round(dt, 3),
                      "rows_per_sec": round(len(batch) / dt, 1) if dt else None})
    return stats
