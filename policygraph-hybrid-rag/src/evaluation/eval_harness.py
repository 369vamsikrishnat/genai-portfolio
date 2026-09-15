from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from src.retrieval.bm25 import build_bm25, search_bm25
from src.retrieval.dense import dense_search, load_all_chunks
from src.retrieval.fusion import (
    extract_fused_chunks,
    reciprocal_rank_fusion,
)
from src.retrieval.reranker import load_reranker, rerank


# ---------------------------------------------------------------------------
# PATHS
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

GOLDEN_SET_PATH = (
    PROJECT_ROOT
    / "src"
    / "evaluation"
    / "golden_set.json"
)

RESULTS_PATH = (
    PROJECT_ROOT
    / "eval"
    / "retrieval_results.json"
)


# ---------------------------------------------------------------------------
# RETRIEVAL CONFIGURATION
# ---------------------------------------------------------------------------

DENSE_TOP_K = 20
BM25_TOP_K = 20
RRF_TOP_K = 10
RRF_K = 60
RERANK_TOP_K = 5


# ---------------------------------------------------------------------------
# TEXT NORMALIZATION
# ---------------------------------------------------------------------------

def normalize_evidence_text(text: str) -> str:
    """
    Normalize text for deterministic evidence matching.

    This handles common formatting differences caused by PDF extraction.

    Examples:
        self-ignition -> self ignition
        inland-waterway -> inland waterway
        Rs.1,500 -> rs 1500
        ` 1500/- -> rs 1500
    """

    if not text:
        return ""

    text = str(text).lower()

    replacements = {
        "\u2010": "-",
        "\u2011": "-",
        "\u2012": "-",
        "\u2013": "-",
        "\u2014": "-",
        "\u2212": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u00a0": " ",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    # Normalize currency symbols.
    text = text.replace("₹", " rs ")
    text = text.replace("`", " rs ")

    # Remove commas between numbers.
    # Example:
    # 1,500 -> 1500
    text = re.sub(
        r"(?<=\d),(?=\d)",
        "",
        text,
    )

    # Normalize Rs / rs.
    text = re.sub(
        r"\brs\.?\s*",
        "rs ",
        text,
    )

    # Convert punctuation and separators into spaces.
    text = re.sub(
        r"[-/,;:()[\]{}]+",
        " ",
        text,
    )

    # Remove punctuation.
    text = re.sub(
        r"[^\w\s]",
        " ",
        text,
    )

    # Collapse whitespace.
    text = re.sub(
        r"\s+",
        " ",
        text,
    ).strip()

    return text


# ---------------------------------------------------------------------------
# EVIDENCE MATCHING
# ---------------------------------------------------------------------------

def phrase_matches(
    content: str,
    evidence_phrases: list[str],
) -> bool:
    """
    Determine whether retrieved chunk content contains
    at least one expected evidence phrase.

    Matching is lexical and deterministic.
    No embeddings or LLMs are used here.
    """

    normalized_content = normalize_evidence_text(
        content
    )

    if not normalized_content:
        return False

    for phrase in evidence_phrases:

        normalized_phrase = normalize_evidence_text(
            phrase
        )

        if not normalized_phrase:
            continue

        if normalized_phrase in normalized_content:
            return True

    return False


# ---------------------------------------------------------------------------
# METADATA MATCHING
# ---------------------------------------------------------------------------

def metadata_matches(
    chunk: dict[str, Any],
    case: dict[str, Any],
) -> bool:
    """
    Match retrieval ground truth using stable document metadata.

    Page number is required.

    Section matching uses the major section because chunk metadata
    currently stores the section heading rather than the clause number.
    """

    expected_page = case.get("source_page")

    if expected_page is None:
        return False

    if chunk.get("page_number") != expected_page:
        return False

    expected_section = str(
        case.get("source_section", "")
    ).strip().lower()

    if not expected_section:
        return True

    chunk_section = str(
        chunk.get("section_number", "")
    ).strip().lower()

    if not chunk_section:
        return False

    expected_major_section = re.split(
        r",\s*clause\s+",
        expected_section,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0].strip()

    return expected_major_section in chunk_section


# ---------------------------------------------------------------------------
# CHUNK RELEVANCE
# ---------------------------------------------------------------------------

def chunk_matches_case(
    chunk: dict[str, Any],
    case: dict[str, Any],
) -> bool:
    """
    Determine whether a retrieved chunk is relevant.

    Retrieval ground truth is based primarily on the authoritative
    source location. Evidence phrases are used as a secondary signal.
    """

    # Primary ground truth: source location.
    if metadata_matches(
        chunk,
        case,
    ):
        return True

    # Secondary validation: textual evidence.
    evidence_phrases = case.get(
        "relevant_evidence",
        [],
    )

    if evidence_phrases:
        return phrase_matches(
            chunk.get(
                "content",
                "",
            ),
            evidence_phrases,
        )

    return False

# ---------------------------------------------------------------------------
# GOLDEN SET
# ---------------------------------------------------------------------------

def load_golden_set() -> list[dict[str, Any]]:
    """
    Load and validate the retrieval golden set.
    """

    if not GOLDEN_SET_PATH.exists():

        raise FileNotFoundError(
            f"Golden set not found: "
            f"{GOLDEN_SET_PATH}"
        )

    with GOLDEN_SET_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:

        data = json.load(
            file
        )

    if not isinstance(
        data,
        list,
    ):

        raise ValueError(
            "Golden set must contain a JSON list."
        )

    required_fields = {
        "id",
        "question",
        "expected_abstention",
    }

    for index, case in enumerate(
        data,
        start=1,
    ):

        missing = (
            required_fields
            - case.keys()
        )

        if missing:

            raise ValueError(
                f"Golden-set case "
                f"{index} "
                f"is missing fields: "
                f"{sorted(missing)}"
            )

    return data


# ---------------------------------------------------------------------------
# RETRIEVAL
# ---------------------------------------------------------------------------

def retrieve_for_evaluation(
    question: str,
    chunks: list[dict[str, Any]],
    bm25,
    reranker,
) -> list[dict[str, Any]]:
    """
    Execute the retrieval stack without generation.

    Pipeline:

        Dense Retrieval
                +
        BM25 Retrieval
                |
                v
        Reciprocal Rank Fusion
                |
                v
        Cross-Encoder Reranking
    """

    # -----------------------------------------------------------------------
    # DENSE RETRIEVAL
    # -----------------------------------------------------------------------

    dense_results = dense_search(
        question,
        top_k=DENSE_TOP_K,
        include_prompt_injection=False,
    )

    # -----------------------------------------------------------------------
    # BM25 RETRIEVAL
    # -----------------------------------------------------------------------

    bm25_results = search_bm25(
        bm25=bm25,
        chunks=chunks,
        query=question,
        top_k=BM25_TOP_K,
    )

    # search_bm25 returns:
    #
    # [
    #     (chunk, score),
    #     (chunk, score),
    # ]
    #
    # Convert BM25 results into chunk dictionaries
    # before fusion.

    bm25_chunks = bm25_results

    # -----------------------------------------------------------------------
    # RECIPROCAL RANK FUSION
    # -----------------------------------------------------------------------

    fused_results = reciprocal_rank_fusion(
        dense_results,
        bm25_chunks,
        k=RRF_K,
    )

    # -----------------------------------------------------------------------
    # EXTRACT FUSED CHUNKS
    # -----------------------------------------------------------------------

    fused_chunks = extract_fused_chunks(fused_results)
    

    fused_chunks = fused_chunks[
        :RRF_TOP_K
    ]

    if not fused_chunks:
        return []

    # -----------------------------------------------------------------------
    # CROSS-ENCODER RERANKING
    # -----------------------------------------------------------------------

    reranked = rerank(
        reranker,
        question,
        fused_chunks,
        top_k=RERANK_TOP_K,
    )

    return normalize_reranked_chunks(
        reranked
    )


# ---------------------------------------------------------------------------
# RERANKER OUTPUT NORMALIZATION
# ---------------------------------------------------------------------------

def normalize_reranked_chunks(
    reranked_results: list[Any],
) -> list[dict[str, Any]]:
    """Convert reranker output into plain chunk dictionaries."""

    normalized: list[dict[str, Any]] = []

    for item in reranked_results:
        if isinstance(item, dict):
            normalized.append(item)
            continue

        if (
            isinstance(item, tuple)
            and len(item) == 2
            and isinstance(item[0], dict)
        ):
            normalized.append(item[0])
            continue

        raise TypeError(
            "Unexpected reranker output item: "
            f"{type(item).__name__}. Expected a chunk dict "
            "or a (chunk, score) tuple."
        )

    return normalized


# ---------------------------------------------------------------------------
# CASE EVALUATION
# ---------------------------------------------------------------------------

def find_relevant_rank(
    retrieved_chunks: list[dict[str, Any]],
    case: dict[str, Any],
) -> int | None:
    """
    Return the 1-based rank of the first
    relevant chunk.

    Returns None when no retrieved chunk
    matches the golden case.
    """

    for rank, chunk in enumerate(
        retrieved_chunks,
        start=1,
    ):

        if chunk_matches_case(
            chunk,
            case,
        ):

            return rank

    return None


def evaluate_case(
    case: dict[str, Any],
    retrieved_chunks: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Evaluate one golden-set case.
    """

    expected_abstention = bool(
        case.get(
            "expected_abstention",
            False,
        )
    )

    # -----------------------------------------------------------------------
    # ABSTENTION CASE
    # -----------------------------------------------------------------------

    if expected_abstention:

        return {
            "id": case["id"],
            "question": case["question"],
            "expected_abstention": True,
            "rank": None,
            "hit_at_1": False,
            "hit_at_3": False,
            "hit_at_5": False,
        }

    # -----------------------------------------------------------------------
    # RETRIEVAL CASE
    # -----------------------------------------------------------------------

    rank = find_relevant_rank(
        retrieved_chunks,
        case,
    )

    return {
        "id": case["id"],
        "question": case["question"],
        "expected_abstention": False,
        "rank": rank,
        "hit_at_1": (
            rank is not None
            and rank <= 1
        ),
        "hit_at_3": (
            rank is not None
            and rank <= 3
        ),
        "hit_at_5": (
            rank is not None
            and rank <= 5
        ),
    }


# ---------------------------------------------------------------------------
# METRICS
# ---------------------------------------------------------------------------

def calculate_metrics(
    results: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Calculate:

        Hit@1
        Hit@3
        Hit@5
        MRR

    Metrics are calculated only over
    retrieval cases.

    Abstention cases are counted separately.
    """

    retrieval_results = [
        result
        for result in results
        if not result[
            "expected_abstention"
        ]
    ]

    total = len(
        retrieval_results
    )

    abstention_cases = (
        len(results)
        - total
    )

    if total == 0:

        return {
            "total_cases": len(results),
            "retrieval_cases": 0,
            "abstention_cases": abstention_cases,
            "hit_at_1": 0.0,
            "hit_at_3": 0.0,
            "hit_at_5": 0.0,
            "mrr": 0.0,
        }

    # -----------------------------------------------------------------------
    # HIT@1
    # -----------------------------------------------------------------------

    hit_at_1 = (
        sum(
            result["hit_at_1"]
            for result
            in retrieval_results
        )
        / total
    )

    # -----------------------------------------------------------------------
    # HIT@3
    # -----------------------------------------------------------------------

    hit_at_3 = (
        sum(
            result["hit_at_3"]
            for result
            in retrieval_results
        )
        / total
    )

    # -----------------------------------------------------------------------
    # HIT@5
    # -----------------------------------------------------------------------

    hit_at_5 = (
        sum(
            result["hit_at_5"]
            for result
            in retrieval_results
        )
        / total
    )

    # -----------------------------------------------------------------------
    # MRR
    # -----------------------------------------------------------------------

    reciprocal_ranks = []

    for result in retrieval_results:

        rank = result[
            "rank"
        ]

        if rank is None:

            reciprocal_ranks.append(
                0.0
            )

        else:

            reciprocal_ranks.append(
                1.0 / rank
            )

    mrr = (
        sum(reciprocal_ranks)
        / total
    )

    return {
        "total_cases": len(results),
        "retrieval_cases": total,
        "abstention_cases": abstention_cases,
        "hit_at_1": round(
            hit_at_1,
            4,
        ),
        "hit_at_3": round(
            hit_at_3,
            4,
        ),
        "hit_at_5": round(
            hit_at_5,
            4,
        ),
        "mrr": round(
            mrr,
            4,
        ),
    }


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main() -> None:

    print(
        "=" * 72
    )

    print(
        "POLICYGRAPH RETRIEVAL EVALUATION"
    )

    print(
        "=" * 72
    )

    print(
        f"Golden set:       "
        f"{GOLDEN_SET_PATH}"
    )

    # -----------------------------------------------------------------------
    # LOAD GOLDEN SET
    # -----------------------------------------------------------------------

    golden_set = load_golden_set()

    print(
        f"Golden cases:     "
        f"{len(golden_set)}"
    )

    # -----------------------------------------------------------------------
    # LOAD DOCUMENT CHUNKS
    # -----------------------------------------------------------------------

    chunks = load_all_chunks(
        include_prompt_injection=False
    )

    print(
        f"Document chunks:  "
        f"{len(chunks)}"
    )

    print()

    # -----------------------------------------------------------------------
    # BUILD BM25
    # -----------------------------------------------------------------------

    print(
        "Building BM25 index..."
    )

    bm25 = build_bm25(
        chunks
    )

    # -----------------------------------------------------------------------
    # RERANKER
    # -----------------------------------------------------------------------

    print(
        "Loading cross-encoder..."
    )
    reranker = load_reranker()
    
    print(
        "Running retrieval evaluation..."
    )

    print()

    results = []

    # -----------------------------------------------------------------------
    # EVALUATE GOLDEN SET
    # -----------------------------------------------------------------------

    for index, case in enumerate(
        golden_set,
        start=1,
    ):

        # -------------------------------------------------------------------
        # ABSTENTION
        # -------------------------------------------------------------------

        if case.get(
            "expected_abstention",
            False,
        ):

            result = evaluate_case(
                case,
                [],
            )

            results.append(
                result
            )

            print(
                f"[{index}/{len(golden_set)}] "
                f"Q{case['id']} "
                f"ABSTENTION"
            )

            continue

        # -------------------------------------------------------------------
        # RETRIEVAL
        # -------------------------------------------------------------------

        retrieved_chunks = retrieve_for_evaluation(
        case["question"], 
                chunks,
                bm25,
                reranker,
        )

        # -------------------------------------------------------------------
        # EVALUATION
        # -------------------------------------------------------------------

        result = evaluate_case(
            case,
            retrieved_chunks,
        )

        results.append(
            result
        )

        rank = result[
            "rank"
        ]

        hit_at_5 = result[
            "hit_at_5"
        ]

        print(
            f"[{index}/{len(golden_set)}] "
            f"Q{case['id']} "
            f"Rank={rank} "
            f"Hit@5={hit_at_5}"
        )

    # -----------------------------------------------------------------------
    # CALCULATE METRICS
    # -----------------------------------------------------------------------

    metrics = calculate_metrics(
        results
    )

    # -----------------------------------------------------------------------
    # PRINT RESULTS
    # -----------------------------------------------------------------------

    print()

    print(
        "=" * 72
    )

    print(
        "FINAL RETRIEVAL METRICS"
    )

    print(
        "=" * 72
    )

    print(
        f"Total cases:       "
        f"{metrics['total_cases']}"
    )

    print(
        f"Retrieval cases:   "
        f"{metrics['retrieval_cases']}"
    )

    print(
        f"Abstention cases:  "
        f"{metrics['abstention_cases']}"
    )

    print(
        f"Hit@1:             "
        f"{metrics['hit_at_1']:.4f}"
    )

    print(
        f"Hit@3:             "
        f"{metrics['hit_at_3']:.4f}"
    )

    print(
        f"Hit@5:             "
        f"{metrics['hit_at_5']:.4f}"
    )

    print(
        f"MRR:               "
        f"{metrics['mrr']:.4f}"
    )

    # -----------------------------------------------------------------------
    # SAVE RESULTS
    # -----------------------------------------------------------------------

    output = {
        "metrics": metrics,
        "results": results,
    }

    RESULTS_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with RESULTS_PATH.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            output,
            file,
            indent=2,
            ensure_ascii=False,
        )

    print()

    print(
        "Results saved to:"
    )

    print(
        RESULTS_PATH
    )


# ---------------------------------------------------------------------------
# RUN
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    main()