from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from google import genai
from google.genai import errors
from google.genai import types
from pydantic import BaseModel
from ragas.embeddings import GoogleEmbeddings
from ragas.llms.base import InstructorBaseRagasLLM
from ragas.metrics.collections import (
    AnswerRelevancy,
    ContextPrecision,
    ContextRecall,
    Faithfulness,
)

from src.pipeline import run_pipeline
from src.api.gemini_model_fallback import get_model_candidates


# ---------------------------------------------------------------------------
# PROJECT CONFIG
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

GOLDEN_SET_PATH = PROJECT_ROOT / "src" / "evaluation" / "golden_set.json"
OUTPUT_PATH = PROJECT_ROOT / "eval" / "ragas_baseline_results.json"

EVALUATION_MODEL = os.getenv(
    "RAGAS_EVALUATION_MODEL",
    "gemini-3.6-flash",
)

EMBEDDING_MODEL = os.getenv(
    "RAGAS_EMBEDDING_MODEL",
    "gemini-embedding-001",
)

RAGAS_SAMPLE_SIZE = int(
    os.getenv(
        "RAGAS_SAMPLE_SIZE",
        "50",
    )
)

RAGAS_AUTO_CONTINUE = os.getenv(
    "RAGAS_AUTO_CONTINUE",
    "true",
).lower() in {
    "1",
    "true",
    "yes",
    "y",
}


# ---------------------------------------------------------------------------
# API KEY
# ---------------------------------------------------------------------------

def get_gemini_api_key() -> str:
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set in the environment."
        )

    return api_key


# ---------------------------------------------------------------------------
# NATIVE GEMINI RAGAS LLM
# ---------------------------------------------------------------------------

class GeminiRagasLLM(InstructorBaseRagasLLM):
    """
    Minimal RAGAS-compatible LLM adapter using the native google-genai SDK.

    This intentionally avoids the Instructor/OpenAI-compatible Gemini path,
    which caused structured-output parsing failures with the current stack.
    """

    def __init__(
        self,
        client: genai.Client,
        model_name: str,
    ) -> None:
        self.client = client
        self.model_name = model_name
        self.model_candidates = get_model_candidates(model_name)

    async def agenerate(
        self,
        prompt: str,
        response_model: type[BaseModel],
        **kwargs: Any,
    ) -> BaseModel:
        response = None
        failures: list[str] = []

        for model in self.model_candidates:
            try:
                response = await self.client.aio.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0,
                        response_mime_type="application/json",
                        response_schema=response_model,
                    ),
                )
                self.model_name = model
                break

            except errors.APIError as exc:
                failures.append(
                    f"{model}: {exc.code} {exc.status}"
                )
                print(
                    f"RAGAS evaluation failed with {model}; "
                    "trying the next model."
                )

            except Exception as exc:
                failures.append(
                    f"{model}: {type(exc).__name__}: {exc}"
                )
                print(
                    f"RAGAS evaluation failed with {model}; "
                    "trying the next model."
                )

        if response is None:
            raise RuntimeError(
                "All RAGAS Gemini models failed: "
                + "; ".join(failures)
            )

        parsed = getattr(response, "parsed", None)

        if parsed is not None:
            return parsed

        response_text = getattr(response, "text", None)

        if not response_text:
            raise RuntimeError(
                "Gemini returned no structured output."
            )

        try:
            payload = json.loads(response_text)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "Gemini returned invalid JSON for a RAGAS structured-output request."
            ) from exc

        return response_model.model_validate(payload)

    def generate(
        self,
        prompt: str,
        response_model: type[BaseModel],
        **kwargs: Any,
    ) -> BaseModel:
        return asyncio.run(
            self.agenerate(
                prompt,
                response_model,
                **kwargs,
            )
        )


def create_ragas_llm():
    return GeminiRagasLLM(
        client=genai.Client(
            api_key=get_gemini_api_key(),
        ),
        model_name=EVALUATION_MODEL,
    )


# ---------------------------------------------------------------------------
# EMBEDDINGS
# ---------------------------------------------------------------------------

def create_ragas_embeddings() -> GoogleEmbeddings:
    api_key = get_gemini_api_key()

    client = genai.Client(
        api_key=api_key,
    )

    return GoogleEmbeddings(
        client=client,
        model=EMBEDDING_MODEL,
    )


# ---------------------------------------------------------------------------
# GOLDEN SET
# ---------------------------------------------------------------------------

def load_golden_set() -> list[dict[str, Any]]:
    with GOLDEN_SET_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def select_sample(
    golden_set: list[dict[str, Any]],
    sample_size: int = RAGAS_SAMPLE_SIZE,
) -> list[dict[str, Any]]:
    answerable_cases = [
        case
        for case in golden_set
        if not case.get(
            "expected_abstention",
            False,
        )
    ]

    if len(answerable_cases) < sample_size:
        raise ValueError(
            f"Need at least {sample_size} answerable cases, "
            f"but only found {len(answerable_cases)}."
        )

    return answerable_cases[:sample_size]


# ---------------------------------------------------------------------------
# CONTEXT
# ---------------------------------------------------------------------------

def build_contexts(
    chunks: list[tuple[dict[str, Any], float]],
) -> list[str]:
    contexts: list[str] = []

    for chunk, _score in chunks:
        content = str(
            chunk.get("content", "")
        ).strip()

        if content:
            contexts.append(content)

    return contexts


# ---------------------------------------------------------------------------
# EVALUATION
# ---------------------------------------------------------------------------

def evaluate_case(
    case: dict[str, Any],
    llm: GeminiRagasLLM,
    embeddings: GoogleEmbeddings,
) -> dict[str, Any]:

    question = case["question"]

    pipeline_result = run_pipeline(
        query=question,
        use_cache=False,
    )

    if not isinstance(pipeline_result, tuple):
        raise TypeError(
            "run_pipeline() must return its standard tuple result."
        )

    answer = pipeline_result[0]
    retrieved_chunks = pipeline_result[1]

    contexts = build_contexts(
        retrieved_chunks,
    )

    return {
        "id": case["id"],
        "question": question,
        "expected_answer": case.get(
            "expected_answer",
            "",
        ),
        "answer": answer,
        "contexts": contexts,
    }


def score_case(
    row: dict[str, Any],
    metrics: list[Any],
) -> dict[str, Any]:
    metric_row: dict[str, Any] = {
        "id": row["id"],
        "question": row["question"],
        "expected_answer": row["expected_answer"],
        "answer": row["answer"],
        "contexts": row["contexts"],
    }

    for metric in metrics:
        metric_name = metric.name

        existing_score = row.get(metric_name)

        if isinstance(existing_score, (int, float)):
            metric_row[metric_name] = existing_score
            print(
                f"  - {metric_name}: already saved, skipping"
            )
            continue

        print(
            f"  - {metric_name}"
        )

        try:
            if metric_name == "faithfulness":
                score = metric.score(
                    user_input=row["question"],
                    response=row["answer"],
                    retrieved_contexts=row["contexts"],
                )

            elif metric_name == "answer_relevancy":
                score = metric.score(
                    user_input=row["question"],
                    response=row["answer"],
                )

            elif metric_name == "context_precision":
                score = metric.score(
                    user_input=row["question"],
                    retrieved_contexts=row["contexts"],
                    reference=row["expected_answer"],
                )

            elif metric_name == "context_recall":
                score = metric.score(
                    user_input=row["question"],
                    retrieved_contexts=row["contexts"],
                    reference=row["expected_answer"],
                )

            else:
                continue

            metric_row[metric_name] = float(score)

        except Exception as exc:
            metric_row[metric_name] = {
                "error": str(exc)
            }

    return metric_row


def load_saved_results() -> dict[int, dict[str, Any]]:
    if not OUTPUT_PATH.exists():
        return {}

    try:
        with OUTPUT_PATH.open(
            "r",
            encoding="utf-8",
        ) as file:
            output = json.load(file)
    except (OSError, json.JSONDecodeError):
        return {}

    return {
        int(row["id"]): row
        for row in output.get("results", [])
        if "id" in row
    }


def save_results(
    results: list[dict[str, Any]],
    sample_size: int,
) -> None:
    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output = {
        "evaluation_model": EVALUATION_MODEL,
        "embedding_model": EMBEDDING_MODEL,
        "sample_size": sample_size,
        "results": results,
    }

    with OUTPUT_PATH.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            output,
            file,
            indent=2,
            ensure_ascii=False,
        )


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main() -> None:

    print("=" * 70)
    print("RAGAS BASELINE EVALUATION")
    print("=" * 70)

    golden_set = load_golden_set()

    sample = select_sample(
        golden_set,
        sample_size=RAGAS_SAMPLE_SIZE,
    )

    print(
        f"Golden set cases: {len(golden_set)}"
    )
    print(
        f"RAGAS sample size: {len(sample)}"
    )
    print(
        f"Evaluation model: {EVALUATION_MODEL}"
    )
    print()

    saved_results = load_saved_results()
    ragas_llm = create_ragas_llm()
    ragas_embeddings = create_ragas_embeddings()

    metrics = [
        Faithfulness(llm=ragas_llm),
        AnswerRelevancy(
            llm=ragas_llm,
            embeddings=ragas_embeddings,
        ),
        ContextPrecision(
            llm=ragas_llm,
        ),
        ContextRecall(
            llm=ragas_llm,
        ),
    ]

    metric_results: list[dict[str, Any]] = [
        saved_results[case["id"]]
        for case in sample
        if case["id"] in saved_results
    ]

    for index, case in enumerate(
        sample,
        start=1,
    ):

        print(
            f"[{index}/{len(sample)}] "
            f"Evaluating {case['id']}: "
            f"{case['question']}"
        )

        saved_row = saved_results.get(case["id"])

        if saved_row and saved_row.get("answer") and saved_row.get("contexts"):
            evaluation_row = saved_row
            print(
                "Using saved answer and contexts; only missing metrics will run."
            )
        else:
            evaluation_row = evaluate_case(
                case,
                ragas_llm,
                ragas_embeddings,
            )

        print(
            f"Scoring {case['id']}..."
        )

        metric_row = score_case(
            evaluation_row,
            metrics,
        )

        metric_results = [
            row
            for row in metric_results
            if row.get("id") != case["id"]
        ]
        metric_results.append(metric_row)

        save_results(
            metric_results,
            sample_size=len(sample),
        )

        print()
        print(json.dumps(metric_row, indent=2, ensure_ascii=False))
        print()

        if index == len(sample):
            break

        if RAGAS_AUTO_CONTINUE:
            continue

        while True:
            confirmation = input(
                "Review this result. Type 'yes' to generate the next question "
                "or 'no' to stop: "
            ).strip().lower()

            if confirmation in {"yes", "y", "next"}:
                break

            if confirmation in {"no", "n", "q", "quit", "exit"}:
                print("Evaluation stopped. Completed results were saved.")
                return

            print("Please type 'yes' to continue or 'no' to stop.")

    print()
    print("=" * 70)
    print("RAGAS EVALUATION COMPLETE")
    print("=" * 70)
    print(
        f"Results saved to: {OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()