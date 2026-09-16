from __future__ import annotations

import csv
import json
import time
from pathlib import Path
from typing import Any

import numpy as np
from sentence_transformers import SentenceTransformer

from src.evaluation.eval_harness import evaluate_case
from src.ingestion.chunker import section_aware_split
from src.ingestion.ocr import load_document_pages

from ablation.chunking_variants import build_fixed_size_chunks


PROJECT_ROOT = Path(__file__).resolve().parents[1]

PDF_PATH = PROJECT_ROOT / "data" / "policy T&C.pdf"
GOLDEN_SET_PATH = (
    PROJECT_ROOT
    / "src"
    / "evaluation"
    / "golden_set.json"
)

RESULTS_DIR = (
    PROJECT_ROOT
    / "ablation"
    / "results"
)

RAW_RESULTS_PATH = (
    RESULTS_DIR
    / "chunking_raw_results.json"
)

SUMMARY_PATH = (
    RESULTS_DIR
    / "chunking_summary.json"
)

METRICS_PATH = (
    RESULTS_DIR
    / "chunking_metrics.csv"
)

EMBEDDING_MODEL_NAME = (
    "BAAI/bge-base-en-v1.5"
)

DENSE_TOP_K = 20
FIXED_CHUNK_SIZE = 200


def load_answerable_cases() -> list[dict[str, Any]]:
    with GOLDEN_SET_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        cases = json.load(file)

    return [
        case
        for case in cases
        if not case.get(
            "expected_abstention",
            False,
        )
    ]


def encode_chunks(
    chunks: list[dict[str, Any]],
    model: SentenceTransformer,
) -> np.ndarray:

    texts = [
        chunk["content"]
        for chunk in chunks
    ]

    return model.encode(
        texts,
        batch_size=32,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=True,
    )


def dense_search_cached(
    query: str,
    chunks: list[dict[str, Any]],
    chunk_embeddings: np.ndarray,
    model: SentenceTransformer,
    top_k: int,
) -> list[tuple[dict[str, Any], float]]:

    query_embedding = model.encode(
        query,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )

    similarities = (
        chunk_embeddings
        @ query_embedding
    )

    top_indices = np.argsort(
        similarities
    )[::-1][:top_k]

    return [
        (
            chunks[index],
            float(similarities[index]),
        )
        for index in top_indices
    ]


def evaluate_configuration(
    cases: list[dict[str, Any]],
    chunks: list[dict[str, Any]],
    chunk_embeddings: np.ndarray,
    model: SentenceTransformer,
) -> tuple[
    list[dict[str, Any]],
    dict[str, float],
]:

    case_results = []

    for case in cases:

        start = time.perf_counter()

        retrieved = dense_search_cached(
            query=case["question"],
            chunks=chunks,
            chunk_embeddings=chunk_embeddings,
            model=model,
            top_k=DENSE_TOP_K,
        )

        latency = (
            time.perf_counter()
            - start
        )

        retrieved_chunks = [
        chunk
        for chunk, _ in retrieved
        ]

        evaluation = evaluate_case(
            case,
        retrieved_chunks,
        )
        case_results.append(
            {
                "id": case["id"],
                "question": case["question"],
                "retrieved": retrieved_chunks,
                "evaluation": evaluation,
                "latency_seconds": latency,
            }
        )

    total = len(case_results)

    hit_at_1 = sum(
        result["evaluation"]["hit_at_1"]
        for result in case_results
    ) / total

    hit_at_3 = sum(
        result["evaluation"]["hit_at_3"]
        for result in case_results
    ) / total

    hit_at_5 = sum(
        result["evaluation"]["hit_at_5"]
        for result in case_results
    ) / total

    mrr = sum(
    (
        1.0 / result["evaluation"]["rank"]
        if result["evaluation"]["rank"] is not None
        else 0.0
    )
    for result in case_results
    ) / total

    avg_latency = sum(
        result["latency_seconds"]
        for result in case_results
    ) / total

    metrics = {
        "recall_at_5": hit_at_5,
        "hit_at_1": hit_at_1,
        "hit_at_3": hit_at_3,
        "hit_at_5": hit_at_5,
        "mrr": mrr,
        "avg_latency_seconds": avg_latency,
    }

    return case_results, metrics


def main() -> None:

    RESULTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    cases = load_answerable_cases()

    print(
        f"Golden-set answerable cases: "
        f"{len(cases)}"
    )

    print(
        "\nLoading source PDF pages..."
    )

    pages = load_document_pages(
        PDF_PATH
    )

    print(
        f"Pages loaded: {len(pages)}"
    )

    print(
        "\nBuilding section-aware chunks..."
    )

    section_chunks = section_aware_split(
        pages=pages,
        doc_name=PDF_PATH.name,
    )

    print(
        f"Section-aware chunks: "
        f"{len(section_chunks)}"
    )

    print(
        "\nBuilding fixed-size chunks..."
    )

    fixed_chunks = build_fixed_size_chunks(
        pages=pages,
        doc_name=PDF_PATH.name,
        chunk_size=FIXED_CHUNK_SIZE,
    )

    print(
        f"Fixed-size chunks: "
        f"{len(fixed_chunks)}"
    )

    print(
        "\nLoading embedding model..."
    )

    model = SentenceTransformer(
        EMBEDDING_MODEL_NAME
    )

    experiments = {
        "section_aware": section_chunks,
        "fixed_size": fixed_chunks,
    }

    raw_results = {
        "experiment":
            "section-aware vs fixed-size chunking",
        "pdf": PDF_PATH.name,
        "fixed_chunk_size":
            FIXED_CHUNK_SIZE,
        "dense_top_k":
            DENSE_TOP_K,
        "embedding_model":
            EMBEDDING_MODEL_NAME,
        "answerable_cases":
            len(cases),
        "configs": {},
    }

    summary = {
        "experiment":
            "section-aware vs fixed-size chunking",
        "configs": {},
    }

    for config_name, chunks in experiments.items():

        print(
            f"\n=== {config_name.upper()} ==="
        )

        print(
            f"Encoding {len(chunks)} chunks..."
        )

        embedding_start = (
            time.perf_counter()
        )

        chunk_embeddings = encode_chunks(
            chunks,
            model,
        )

        embedding_time = (
            time.perf_counter()
            - embedding_start
        )

        print(
            f"Embedding completed in "
            f"{embedding_time:.2f}s"
        )

        case_results, metrics = (
            evaluate_configuration(
                cases=cases,
                chunks=chunks,
                chunk_embeddings=chunk_embeddings,
                model=model,
            )
        )

        raw_results["configs"][
            config_name
        ] = {
            "chunk_count": len(chunks),
            "embedding_time_seconds":
                embedding_time,
            "results": case_results,
        }

        summary["configs"][
            config_name
        ] = {
            "chunk_count": len(chunks),
            "embedding_time_seconds":
                embedding_time,
            "metrics": metrics,
        }

        print(
            f"Recall@5: "
            f"{metrics['recall_at_5']:.4f}"
        )

        print(
            f"Hit@1:    "
            f"{metrics['hit_at_1']:.4f}"
        )

        print(
            f"Hit@3:    "
            f"{metrics['hit_at_3']:.4f}"
        )

        print(
            f"Hit@5:    "
            f"{metrics['hit_at_5']:.4f}"
        )

        print(
            f"MRR:      "
            f"{metrics['mrr']:.4f}"
        )

        print(
            f"Avg query latency: "
            f"{metrics['avg_latency_seconds']:.4f}s"
        )

    with RAW_RESULTS_PATH.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            raw_results,
            file,
            indent=2,
        )

    with SUMMARY_PATH.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            summary,
            file,
            indent=2,
        )

    with METRICS_PATH.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.writer(file)

        writer.writerow(
            [
                "config",
                "chunk_count",
                "embedding_time_seconds",
                "recall_at_5",
                "hit_at_1",
                "hit_at_3",
                "hit_at_5",
                "mrr",
                "avg_latency_seconds",
            ]
        )

        for config_name, config_data in (
            summary["configs"].items()
        ):

            metrics = config_data[
                "metrics"
            ]

            writer.writerow(
                [
                    config_name,
                    config_data[
                        "chunk_count"
                    ],
                    config_data[
                        "embedding_time_seconds"
                    ],
                    metrics[
                        "recall_at_5"
                    ],
                    metrics[
                        "hit_at_1"
                    ],
                    metrics[
                        "hit_at_3"
                    ],
                    metrics[
                        "hit_at_5"
                    ],
                    metrics["mrr"],
                    metrics[
                        "avg_latency_seconds"
                    ],
                ]
            )

    print("\n=== SAVED ===")
    print(RAW_RESULTS_PATH)
    print(SUMMARY_PATH)
    print(METRICS_PATH)


if __name__ == "__main__":
    main()