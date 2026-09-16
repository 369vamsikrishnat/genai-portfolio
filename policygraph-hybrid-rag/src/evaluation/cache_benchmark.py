from __future__ import annotations

import json
import statistics
import time
from pathlib import Path

from src.api.cost_tracker import CostTracker
from src.pipeline import run_pipeline, get_semantic_cache


QUERY = (
    "What events are covered under Section I "
    "for loss or damage to the insured vehicle?"
)

REPETITIONS = 3

COMPARISON_FILE = Path(
    "eval/comparison_results.md"
)


def run_once(
    query: str,
    use_cache: bool,
):
    tracker = CostTracker()

    start = time.perf_counter()

    (
        answer,
        results,
        timings,
        cost,
        tracker,
    ) = run_pipeline(
        query=query,
        tracker=tracker,
        use_cache=use_cache,
    )

    total_latency = (
        time.perf_counter() - start
    )

    return {
        "answer": answer,
        "latency": total_latency,
        "cost": cost or 0.0,
        "timings": timings,
        "tracker": tracker.snapshot(),
    }


def benchmark_without_cache():
    print("\n" + "=" * 60)
    print("WITHOUT CACHE")
    print("=" * 60)

    results = []

    for i in range(
        1,
        REPETITIONS + 1,
    ):
        print(
            f"\nRun {i}/{REPETITIONS}"
        )

        result = run_once(
            query=QUERY,
            use_cache=False,
        )

        results.append(result)

        print(
            f"Latency: {result['latency']:.4f}s"
        )
        print(
            f"Cost: ${result['cost']:.6f}"
        )

    return results


def benchmark_with_cache():
    print("\n" + "=" * 60)
    print("WITH CACHE")
    print("=" * 60)

    cache = get_semantic_cache()

    cache.client.flushdb()

    print(
        "\nRedis cache cleared."
    )

    results = []

    for i in range(
        1,
        REPETITIONS + 1,
    ):
        print(
            f"\nRun {i}/{REPETITIONS}"
        )

        result = run_once(
            query=QUERY,
            use_cache=True,
        )

        results.append(result)

        print(
            f"Latency: {result['latency']:.4f}s"
        )
        print(
            f"Cost: ${result['cost']:.6f}"
        )
        print(
            f"Cache hit: "
            f"{result['timings'].get('cache_hit', 0.0)}"
        )

    return results


def average(
    values: list[float],
) -> float:
    return statistics.mean(values)


def calculate_metrics(
    without_cache,
    with_cache,
):
    without_latencies = [
        result["latency"]
        for result in without_cache
    ]

    with_latencies = [
        result["latency"]
        for result in with_cache
    ]

    without_costs = [
        result["cost"]
        for result in without_cache
    ]

    with_costs = [
        result["cost"]
        for result in with_cache
    ]

    without_avg_latency = average(
        without_latencies
    )

    with_avg_latency = average(
        with_latencies
    )

    without_total_cost = sum(
        without_costs
    )

    with_total_cost = sum(
        with_costs
    )

    latency_savings = (
        (
            without_avg_latency
            - with_avg_latency
        )
        / without_avg_latency
        * 100
        if without_avg_latency
        else 0.0
    )

    cost_savings = (
        (
            without_total_cost
            - with_total_cost
        )
        / without_total_cost
        * 100
        if without_total_cost
        else 0.0
    )

    cache = get_semantic_cache()

    return {
        "without_cache": {
            "average_latency": without_avg_latency,
            "total_cost": without_total_cost,
        },
        "with_cache": {
            "average_latency": with_avg_latency,
            "total_cost": with_total_cost,
        },
        "latency_savings_percent": latency_savings,
        "cost_savings_percent": cost_savings,
        "cache_stats": cache.stats(),
    }


def update_comparison_file(
    metrics: dict,
):
    existing = ""

    if COMPARISON_FILE.exists():
        existing = (
            COMPARISON_FILE.read_text(
                encoding="utf-8"
            )
        )

    marker = "\n## Day 14 — Semantic Cache Benchmark\n"

    if marker in existing:
        existing = existing.split(
            marker,
            1,
        )[0]

    without_cache = metrics[
        "without_cache"
    ]

    with_cache = metrics[
        "with_cache"
    ]

    cache_stats = metrics[
        "cache_stats"
    ]

    section = f"""
## Day 14 — Semantic Cache Benchmark

### Benchmark Configuration

- Query: `{QUERY}`
- Repetitions: {REPETITIONS}
- Semantic similarity threshold: {cache_stats["similarity_threshold"]}
- Cache TTL: {cache_stats["ttl_seconds"]} seconds

### Cost and Latency

| Configuration | Avg Latency | Total Cost |
|---|---:|---:|
| Without Cache | {without_cache["average_latency"]:.4f}s | ${without_cache["total_cost"]:.6f} |
| With Cache | {with_cache["average_latency"]:.4f}s | ${with_cache["total_cost"]:.6f} |

### Cache Performance

| Metric | Result |
|---|---:|
| Cache Hits | {cache_stats["hits"]} |
| Cache Misses | {cache_stats["misses"]} |
| Total Cache Requests | {cache_stats["total_requests"]} |
| Cache Hit Rate | {cache_stats["hit_rate"] * 100:.2f}% |
| Latency Savings | {metrics["latency_savings_percent"]:.2f}% |
| Cost Savings | {metrics["cost_savings_percent"]:.2f}% |

### Notes

The benchmark repeats the same query multiple times.

Without cache, every request executes the full retrieval and generation pipeline.

With cache, the first request populates Redis and subsequent semantically equivalent requests can return the cached answer without executing the retrieval, reranking, or generation stages.

The measured results are specific to this benchmark query, repetition count, model configuration, and local environment.
"""

    COMPARISON_FILE.write_text(
        existing.rstrip()
        + "\n"
        + section.strip()
        + "\n",
        encoding="utf-8",
    )


def main():
    print("\n" + "#" * 60)
    print("DAY 14 — CACHE BENCHMARK")
    print("#" * 60)

    # ---------------------------------------------------------
    # Warm up local models and clients.
    # This prevents model-loading overhead from dominating
    # the benchmark.
    # ---------------------------------------------------------

    print("\nWarming up pipeline...")

    warmup_tracker = CostTracker()

    run_pipeline(
        query=(
            "What is covered under the motor insurance policy?"
        ),
        tracker=warmup_tracker,
        use_cache=False,
    )

    # ---------------------------------------------------------
    # Run benchmarks
    # ---------------------------------------------------------

    without_cache = (
        benchmark_without_cache()
    )

    with_cache = (
        benchmark_with_cache()
    )

    # ---------------------------------------------------------
    # Calculate metrics
    # ---------------------------------------------------------

    metrics = calculate_metrics(
        without_cache=without_cache,
        with_cache=with_cache,
    )

    # ---------------------------------------------------------
    # Display results
    # ---------------------------------------------------------

    print("\n" + "#" * 60)
    print("FINAL RESULTS")
    print("#" * 60)

    print(
        "\nWITHOUT CACHE"
    )
    print(
        f"Average latency: "
        f"{metrics['without_cache']['average_latency']:.4f}s"
    )
    print(
        f"Total cost: "
        f"${metrics['without_cache']['total_cost']:.6f}"
    )

    print(
        "\nWITH CACHE"
    )
    print(
        f"Average latency: "
        f"{metrics['with_cache']['average_latency']:.4f}s"
    )
    print(
        f"Total cost: "
        f"${metrics['with_cache']['total_cost']:.6f}"
    )

    print(
        "\nCACHE"
    )
    print(
        f"Hits: "
        f"{metrics['cache_stats']['hits']}"
    )
    print(
        f"Misses: "
        f"{metrics['cache_stats']['misses']}"
    )
    print(
        f"Hit rate: "
        f"{metrics['cache_stats']['hit_rate'] * 100:.2f}%"
    )

    print(
        "\nSAVINGS"
    )
    print(
        f"Latency savings: "
        f"{metrics['latency_savings_percent']:.2f}%"
    )
    print(
        f"Cost savings: "
        f"{metrics['cost_savings_percent']:.2f}%"
    )

    # ---------------------------------------------------------
    # Save machine-readable results
    # ---------------------------------------------------------

    output_path = Path(
        "eval/cache_benchmark_results.json"
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_text(
        json.dumps(
            {
                "query": QUERY,
                "repetitions": REPETITIONS,
                "without_cache": without_cache,
                "with_cache": with_cache,
                "metrics": metrics,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    # ---------------------------------------------------------
    # Update Day 14 comparison document
    # ---------------------------------------------------------

    update_comparison_file(
        metrics
    )

    print(
        "\nSaved:"
    )
    print(
        "eval/cache_benchmark_results.json"
    )
    print(
        "eval/comparison_results.md"
    )


if __name__ == "__main__":
    main()