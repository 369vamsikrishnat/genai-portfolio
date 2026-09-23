from __future__ import annotations

import json
import statistics
import time
from pathlib import Path
from typing import Any

from src.api.cost_tracker import CostTracker
from src.pipeline import get_semantic_cache, run_pipeline


TEST_SET_PATH = Path(
    "src/evaluation/semantic_cache_test_set.json"
)
OFF_REPETITIONS = 1
ON_REPETITIONS = 2
RESULTS_PATH = Path("eval/cache_benchmark_results.json")
COMPARISON_PATH = Path("eval/comparison_results.md")


def load_queries() -> list[dict[str, Any]]:
    with TEST_SET_PATH.open("r", encoding="utf-8") as file:
        queries = json.load(file)

    if not isinstance(queries, list) or not queries:
        raise ValueError("Semantic cache test set must be a non-empty list.")

    for query in queries:
        if "id" not in query or "question" not in query:
            raise ValueError("Each test-set item needs id and question.")

    return queries


def run_request(
    query_id: str,
    query: str,
    cache_enabled: bool,
    request_number: int,
) -> dict[str, Any]:
    tracker = CostTracker()
    started = time.perf_counter()

    answer, _results, timings, cost, _tracker = run_pipeline(
        query=query,
        tracker=tracker,
        use_cache=cache_enabled,
    )

    latency_ms = (time.perf_counter() - started) * 1000
    cache_hit = bool(timings.get("cache_hit", 0.0))
    generation_model = timings.get("generation_model")

    return {
        "run_id": None,
        "query_id": query_id,
        "query": query,
        "cache": "ON" if cache_enabled else "OFF",
        "request_number": request_number,
        "cache_result": (
            ("HIT" if cache_hit else "MISS")
            if cache_enabled
            else "N/A"
        ),
        "gemini_called": not cache_hit,
        "gemini_model": generation_model,
        "latency_ms": round(latency_ms, 3),
        "input_tokens": int(timings.get("input_tokens", 0)),
        "output_tokens": int(timings.get("output_tokens", 0)),
        "thinking_tokens": int(timings.get("thinking_tokens", 0)),
        "total_tokens": (
            int(timings.get("input_tokens", 0))
            + int(timings.get("output_tokens", 0))
            + int(timings.get("thinking_tokens", 0))
        ),
        "llm_cost_usd": round(float(cost or 0.0), 10),
        "answer": answer,
    }


def run_group(
    queries: list[dict[str, Any]],
    cache_enabled: bool,
    next_run_id: int,
) -> tuple[list[dict[str, Any]], int]:
    rows: list[dict[str, Any]] = []
    repetitions = ON_REPETITIONS if cache_enabled else OFF_REPETITIONS

    for query in queries:
        query_id = f"Q{int(query['id']):02d}"

        for request_number in range(1, repetitions + 1):
            print(
                f"{('CACHE ON' if cache_enabled else 'CACHE OFF')} "
                f"{query_id} request {request_number}/{repetitions}"
            )
            row = run_request(
                query_id,
                query["question"],
                cache_enabled,
                request_number,
            )
            row["run_id"] = next_run_id
            rows.append(row)
            next_run_id += 1

    return rows, next_run_id


def aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    requests = len(rows)
    hits = sum(row["cache_result"] == "HIT" for row in rows)
    misses = sum(row["cache_result"] == "MISS" for row in rows)
    calls = sum(row["gemini_called"] for row in rows)
    latencies = [row["latency_ms"] for row in rows]
    total_cost = sum(row["llm_cost_usd"] for row in rows)

    return {
        "total_requests": requests,
        "cache_hits": hits,
        "cache_misses": misses,
        "gemini_calls": calls,
        "total_input_tokens": sum(row["input_tokens"] for row in rows),
        "total_output_tokens": sum(row["output_tokens"] for row in rows),
        "total_thinking_tokens": sum(row["thinking_tokens"] for row in rows),
        "total_tokens": sum(row["total_tokens"] for row in rows),
        "total_llm_cost_usd": total_cost,
        "average_cost_per_request_usd": (
            total_cost / requests if requests else 0.0
        ),
        "average_latency_ms": statistics.mean(latencies) if latencies else 0.0,
        "minimum_latency_ms": min(latencies) if latencies else 0.0,
        "maximum_latency_ms": max(latencies) if latencies else 0.0,
        "cache_hit_rate": hits / requests if requests else 0.0,
    }


def percent_change(before: float, after: float) -> float:
    return ((before - after) / before * 100) if before else 0.0


def write_report(
    rows: list[dict[str, Any]],
    off: dict[str, Any],
    on: dict[str, Any],
    cache: Any,
) -> None:
    cost_savings = off["total_llm_cost_usd"] - on["total_llm_cost_usd"]
    latency_reduction = off["average_latency_ms"] - on["average_latency_ms"]
    comparison = {
        "gemini_calls_avoided": off["gemini_calls"] - on["gemini_calls"],
        "cost_savings_usd": cost_savings,
        "cost_savings_percent": percent_change(
            off["total_llm_cost_usd"],
            on["total_llm_cost_usd"],
        ),
        "latency_reduction_ms": latency_reduction,
        "latency_reduction_percent": percent_change(
            off["average_latency_ms"],
            on["average_latency_ms"],
        ),
    }

    raw_lines = [
        "| Run ID | Query ID | Cache | Request # | Cache Result | Gemini Called | Gemini Model | Latency (ms) | Input Tokens | Output Tokens | Total Tokens | LLM Cost ($) |",
        "|---:|---|---|---:|---|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        raw_lines.append(
            f"| {row['run_id']} | {row['query_id']} | {row['cache']} | "
            f"{row['request_number']} | {row['cache_result']} | "
            f"{'Yes' if row['gemini_called'] else 'No'} | "
            f"{row['gemini_model'] or '-'} | {row['latency_ms']:.3f} | "
            f"{row['input_tokens']} | {row['output_tokens']} | "
            f"{row['total_tokens']} | {row['llm_cost_usd']:.10f} |"
        )

    summary_lines = [
        "| Metric | Cache OFF | Cache ON |",
        "|---|---:|---:|",
    ]
    summary_metrics = (
        ("Total requests", "total_requests", ""),
        ("Cache hits", "cache_hits", ""),
        ("Cache misses", "cache_misses", ""),
        ("Gemini calls", "gemini_calls", ""),
        ("Total input tokens", "total_input_tokens", ""),
        ("Total output tokens", "total_output_tokens", ""),
        ("Total LLM cost ($)", "total_llm_cost_usd", ".10f"),
        ("Average cost/request ($)", "average_cost_per_request_usd", ".10f"),
        ("Average latency (ms)", "average_latency_ms", ".3f"),
        ("Minimum latency (ms)", "minimum_latency_ms", ".3f"),
        ("Maximum latency (ms)", "maximum_latency_ms", ".3f"),
        ("Cache hit rate", "cache_hit_rate", ".2%"),
    )
    for label, key, format_spec in summary_metrics:
        off_value = format(off[key], format_spec) if format_spec else str(off[key])
        on_value = format(on[key], format_spec) if format_spec else str(on[key])
        if "$" in label:
            off_value = "$" + off_value
            on_value = "$" + on_value
        summary_lines.append(f"| {label} | {off_value} | {on_value} |")

    report = f"""# Redis Semantic Cache Benchmark

Test set: `{TEST_SET_PATH}`  
Unique queries: `{len({row['query_id'] for row in rows})}`  
Cache OFF repetitions: `{OFF_REPETITIONS}`  
Cache ON repetitions: `{ON_REPETITIONS}`  
Similarity threshold: `{cache.similarity_threshold}`  
TTL: `{cache.ttl_seconds}` seconds

## Raw Experiment Table

{chr(10).join(raw_lines)}

## Summary Table

{chr(10).join(summary_lines)}

## Cache Impact

| Metric | Value |
|---|---:|
| Gemini calls avoided | {comparison['gemini_calls_avoided']} |
| Cost savings ($) | {comparison['cost_savings_usd']:.10f} |
| Cost savings (%) | {comparison['cost_savings_percent']:.2f}% |
| Latency reduction (ms) | {comparison['latency_reduction_ms']:.3f} |
| Latency reduction (%) | {comparison['latency_reduction_percent']:.2f}% |

## Project Story

Redis semantic caching achieved **{on['cache_hit_rate']:.2%} cache hit rate**, avoiding **{comparison['gemini_calls_avoided']} Gemini calls**, reducing LLM cost by **{comparison['cost_savings_percent']:.2f}%**, and reducing average response latency by **{comparison['latency_reduction_percent']:.2f}%** across this repeated-query workload.
"""

    COMPARISON_PATH.parent.mkdir(parents=True, exist_ok=True)
    COMPARISON_PATH.write_text(report, encoding="utf-8")

    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(
        json.dumps(
            {
                "test_set": str(TEST_SET_PATH),
                "query_count": len({row["query_id"] for row in rows}),
                "off_repetitions": OFF_REPETITIONS,
                "on_repetitions": ON_REPETITIONS,
                "raw_requests": rows,
                "summary": {"cache_off": off, "cache_on": on},
                "comparison": comparison,
                "cache_configuration": cache.stats(),
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def main() -> None:
    queries = load_queries()
    cache = get_semantic_cache()
    cache.client.flushdb()

    print("Running cache OFF benchmark...")
    off_rows, next_run_id = run_group(queries, False, 1)

    cache.client.flushdb()
    print("Running cache ON benchmark...")
    on_rows, _ = run_group(queries, True, next_run_id)

    rows = off_rows + on_rows
    write_report(
        rows,
        aggregate(off_rows),
        aggregate(on_rows),
        cache,
    )
    print(f"Saved {COMPARISON_PATH}")
    print(f"Saved {RESULTS_PATH}")


if __name__ == "__main__":
    main()
