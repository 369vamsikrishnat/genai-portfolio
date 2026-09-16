from __future__ import annotations

import csv
import json
import time
from pathlib import Path
from typing import Any

from src.retrieval.bm25 import build_bm25
from src.retrieval.dense import load_all_chunks
from src.retrieval.reranker import load_reranker

from ablation.retrieval_variants import (
    ABLATION_CONFIGS,
    retrieve_with_stages,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]

GOLDEN_SET_PATH = (
    PROJECT_ROOT / "src" / "evaluation" / "golden_set.json"
)

RESULTS_DIR = PROJECT_ROOT / "ablation" / "results"

RAW_RESULTS_PATH = RESULTS_DIR / "raw_results.json"
SUMMARY_PATH = RESULTS_DIR / "summary.json"
METRICS_PATH = RESULTS_DIR / "metrics.csv"


def normalize_text(text: str) -> str:
    return " ".join(text.lower().split())


def phrase_matches(
    content: str,
    evidence_phrases: list[str],
) -> bool:
    normalized_content = normalize_text(content)

    for phrase in evidence_phrases:
        normalized_phrase = normalize_text(phrase)

        if (
            normalized_phrase
            and normalized_phrase in normalized_content
        ):
            return True

    return False


def metadata_matches(
    chunk: dict[str, Any],
    case: dict[str, Any],
) -> bool:

    expected_page = case.get("source_page")
    actual_page = chunk.get("page_number")

    if (
        expected_page is not None
        and actual_page != expected_page
    ):
        return False

    expected_section = case.get("source_section")

    if not expected_section:
        return True

    actual_section = str(
        chunk.get("section_number", "")
    ).lower()

    expected_section = str(
        expected_section
    ).lower()

    expected_major = (
        expected_section
        .split(", clause")[0]
        .strip()
    )

    return expected_major in actual_section


def chunk_matches_case(
    chunk: dict[str, Any],
    case: dict[str, Any],
) -> bool:

    if not metadata_matches(chunk, case):
        return False

    evidence_phrases = case.get("evidence", [])

    if not evidence_phrases:
        return True

    return phrase_matches(
        chunk.get("content", ""),
        evidence_phrases,
    )


def find_relevant_rank(
    retrieved_chunks: list[tuple[dict[str, Any], float]],
    case: dict[str, Any],
) -> int | None:

    for rank, (chunk, _score) in enumerate(
        retrieved_chunks,
        start=1,
    ):
        if chunk_matches_case(chunk, case):
            return rank

    return None


def serialize_results(
    retrieved_chunks: list[tuple[dict[str, Any], float]],
    limit: int,
) -> list[dict[str, Any]]:

    return [
        {
            "rank": rank,
            "chunk_id": chunk.get("chunk_id"),
            "doc_name": chunk.get("doc_name"),
            "page_number": chunk.get("page_number"),
            "section_number": chunk.get("section_number"),
            "section_title": chunk.get("section_title"),
            "score": score,
        }
        for rank, (chunk, score) in enumerate(
            retrieved_chunks[:limit],
            start=1,
        )
    ]


def evaluate_case(
    case: dict[str, Any],
    retrieved_chunks: list[tuple[dict[str, Any], float]],
) -> dict[str, Any]:

    relevant_rank = find_relevant_rank(
        retrieved_chunks,
        case,
    )

    return {
        "id": case["id"],
        "question": case["question"],
        "relevant_rank": relevant_rank,
        "hit_at_1": (
            relevant_rank is not None
            and relevant_rank <= 1
        ),
        "hit_at_3": (
            relevant_rank is not None
            and relevant_rank <= 3
        ),
        "hit_at_5": (
            relevant_rank is not None
            and relevant_rank <= 5
        ),
    }


def calculate_metrics(
    case_results: list[dict[str, Any]],
) -> dict[str, float]:

    total = len(case_results)

    if total == 0:
        return {
            "recall_at_5": 0.0,
            "hit_at_1": 0.0,
            "hit_at_3": 0.0,
            "hit_at_5": 0.0,
            "mrr": 0.0,
        }

    hit_at_1 = sum(
        result["hit_at_1"]
        for result in case_results
    )

    hit_at_3 = sum(
        result["hit_at_3"]
        for result in case_results
    )

    hit_at_5 = sum(
        result["hit_at_5"]
        for result in case_results
    )

    reciprocal_ranks = []

    for result in case_results:

        rank = result["relevant_rank"]

        if rank is not None:
            reciprocal_ranks.append(1.0 / rank)
        else:
            reciprocal_ranks.append(0.0)

    return {
        "recall_at_5": hit_at_5 / total,
        "hit_at_1": hit_at_1 / total,
        "hit_at_3": hit_at_3 / total,
        "hit_at_5": hit_at_5 / total,
        "mrr": sum(reciprocal_ranks) / total,
    }


def main() -> None:

    RESULTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print("\n" + "=" * 80)
    print("DAY 13 — RETRIEVAL ABLATION STUDY")
    print("=" * 80)

    # ------------------------------------------------------------------
    # Load golden set
    # ------------------------------------------------------------------

    with GOLDEN_SET_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:

        golden_set = json.load(file)

    answerable_cases = [
        case
        for case in golden_set
        if not case.get(
            "expected_abstention",
            False,
        )
    ]

    print(
        f"\nGolden-set cases: {len(golden_set)}"
    )

    print(
        f"Answerable cases: {len(answerable_cases)}"
    )

    print(
        f"Abstention cases: "
        f"{len(golden_set) - len(answerable_cases)}"
    )

    # ------------------------------------------------------------------
    # Load retrieval resources
    # ------------------------------------------------------------------

    print("\nLoading indexed chunks...")

    chunks = load_all_chunks(
        include_prompt_injection=False
    )

    if not chunks:
        raise RuntimeError(
            "No indexed chunks found."
        )

    print(
        f"Indexed chunks: {len(chunks)}"
    )

    print("\nBuilding retrieval resources...")

    bm25 = build_bm25(chunks)

    reranker = load_reranker()

    # ------------------------------------------------------------------
    # Storage
    # ------------------------------------------------------------------

    all_case_results = []

    total_latency = {
        "dense": 0.0,
        "bm25": 0.0,
        "rrf": 0.0,
        "reranked": 0.0,
    }

    # ------------------------------------------------------------------
    # Run every question ONCE
    # ------------------------------------------------------------------

    for index, case in enumerate(
        answerable_cases,
        start=1,
    ):

        question = case["question"]

        print("\n" + "-" * 80)

        print(
            f"[{index:02d}/{len(answerable_cases)}] "
            f"{question}"
        )

        start = time.perf_counter()

        stages = retrieve_with_stages(
            query=question,
            chunks=chunks,
            bm25=bm25,
            reranker=reranker,
        )

        total_query_latency = (
            time.perf_counter() - start
        )

        # --------------------------------------------------------------
        # Evaluate every retrieval stage
        # --------------------------------------------------------------

        case_data = {
            "id": case["id"],
            "question": question,
            "stages": {},
        }

        for stage_name, stage_results in stages.items():

            stage_start = time.perf_counter()

            evaluation = evaluate_case(
                case=case,
                retrieved_chunks=stage_results,
            )

            stage_latency = (
                time.perf_counter() - stage_start
            )

            total_latency[stage_name] += (
                stage_latency
            )

            evaluation["results"] = (
                serialize_results(
                    stage_results,
                    limit=20,
                )
            )

            case_data["stages"][stage_name] = (
                evaluation
            )

        all_case_results.append(case_data)

        # --------------------------------------------------------------
        # Print selected configuration results
        # --------------------------------------------------------------

        dense_rank = (
            case_data["stages"]["dense"]
            ["relevant_rank"]
        )

        rrf_rank = (
            case_data["stages"]["rrf"]
            ["relevant_rank"]
        )

        reranked_rank = (
            case_data["stages"]["reranked"]
            ["relevant_rank"]
        )

        print(
            f"  Dense:    rank={dense_rank}"
        )

        print(
            f"  RRF:      rank={rrf_rank}"
        )

        print(
            f"  Reranked: rank={reranked_rank}"
        )

        print(
            f"  Pipeline retrieval time: "
            f"{total_query_latency:.3f}s"
        )

    # ------------------------------------------------------------------
    # Calculate configuration metrics
    # ------------------------------------------------------------------

    configuration_stage_map = {
        "dense_only": "dense",
        "hybrid": "rrf",
        "hybrid_reranked": "reranked",
    }

    all_results = {}

    print("\n" + "=" * 80)
    print("CONFIGURATION RESULTS")
    print("=" * 80)

    for config_key, stage_name in (
        configuration_stage_map.items()
    ):

        config_metadata = ABLATION_CONFIGS[
            config_key
        ]

        case_results = []

        for case_data in all_case_results:

            stage_result = (
                case_data["stages"][stage_name]
            )

            case_results.append(
                {
                    "id": case_data["id"],
                    "question": case_data[
                        "question"
                    ],
                    "relevant_rank": (
                        stage_result[
                            "relevant_rank"
                        ]
                    ),
                    "hit_at_1": (
                        stage_result[
                            "hit_at_1"
                        ]
                    ),
                    "hit_at_3": (
                        stage_result[
                            "hit_at_3"
                        ]
                    ),
                    "hit_at_5": (
                        stage_result[
                            "hit_at_5"
                        ]
                    ),
                }
            )

        metrics = calculate_metrics(
            case_results
        )

        all_results[config_key] = {
            "configuration": config_metadata,
            "metrics": metrics,
            "cases": case_results,
        }

        print("\n" + "-" * 80)

        print(
            f"CONFIGURATION: "
            f"{config_metadata['name']}"
        )

        print("-" * 80)

        print(
            f"Recall@5: {metrics['recall_at_5']:.4f}"
        )

        print(
            f"Hit@1:    {metrics['hit_at_1']:.4f}"
        )

        print(
            f"Hit@3:    {metrics['hit_at_3']:.4f}"
        )

        print(
            f"Hit@5:    {metrics['hit_at_5']:.4f}"
        )

        print(
            f"MRR:      {metrics['mrr']:.4f}"
        )

    # ------------------------------------------------------------------
    # Stage metrics
    # ------------------------------------------------------------------

    stage_metrics = {}

    for stage_name in [
        "dense",
        "bm25",
        "rrf",
        "reranked",
    ]:

        stage_case_results = []

        for case_data in all_case_results:

            stage_result = (
                case_data["stages"][stage_name]
            )

            stage_case_results.append(
                {
                    "relevant_rank": (
                        stage_result[
                            "relevant_rank"
                        ]
                    ),
                    "hit_at_1": (
                        stage_result[
                            "hit_at_1"
                        ]
                    ),
                    "hit_at_3": (
                        stage_result[
                            "hit_at_3"
                        ]
                    ),
                    "hit_at_5": (
                        stage_result[
                            "hit_at_5"
                        ]
                    ),
                }
            )

        stage_metrics[stage_name] = (
            calculate_metrics(
                stage_case_results
            )
        )

    # ------------------------------------------------------------------
    # Save raw results
    # ------------------------------------------------------------------

    raw_output = {
        "experiment": {
            "name": "retrieval_ablation",
            "golden_set_cases": len(golden_set),
            "answerable_cases": len(
                answerable_cases
            ),
            "indexed_chunks": len(chunks),
        },
        "configurations": all_results,
        "stage_metrics": stage_metrics,
        "cases": all_case_results,
    }

    with RAW_RESULTS_PATH.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            raw_output,
            file,
            indent=2,
        )

    # ------------------------------------------------------------------
    # Save summary
    # ------------------------------------------------------------------

    summary = {
        "configurations": all_results,
        "stage_metrics": stage_metrics,
    }

    with SUMMARY_PATH.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            summary,
            file,
            indent=2,
        )

    # ------------------------------------------------------------------
    # Save CSV
    # ------------------------------------------------------------------

    with METRICS_PATH.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.writer(file)

        writer.writerow(
            [
                "configuration",
                "recall_at_5",
                "hit_at_1",
                "hit_at_3",
                "hit_at_5",
                "mrr",
            ]
        )

        for config_key, result in (
            all_results.items()
        ):

            metrics = result["metrics"]

            writer.writerow(
                [
                    config_key,
                    metrics["recall_at_5"],
                    metrics["hit_at_1"],
                    metrics["hit_at_3"],
                    metrics["hit_at_5"],
                    metrics["mrr"],
                ]
            )

    # ------------------------------------------------------------------
    # Final stage summary
    # ------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("RETRIEVAL STAGE SUMMARY")
    print("=" * 80)

    for stage_name, metrics in (
        stage_metrics.items()
    ):

        print(
            f"\n{stage_name.upper()}"
        )

        print(
            f"  Recall@5: {metrics['recall_at_5']:.4f}"
        )

        print(
            f"  Hit@1:    {metrics['hit_at_1']:.4f}"
        )

        print(
            f"  Hit@3:    {metrics['hit_at_3']:.4f}"
        )

        print(
            f"  Hit@5:    {metrics['hit_at_5']:.4f}"
        )

        print(
            f"  MRR:      {metrics['mrr']:.4f}"
        )

    print("\n" + "=" * 80)
    print("ABLATION COMPLETE")
    print("=" * 80)

    print(
        f"\nRaw results: {RAW_RESULTS_PATH}"
    )

    print(
        f"Summary:     {SUMMARY_PATH}"
    )

    print(
        f"Metrics CSV: {METRICS_PATH}"
    )


if __name__ == "__main__":
    main()