from __future__ import annotations

import os
from collections.abc import Iterable

from google import genai
from google.genai import errors


DEFAULT_MODEL_CANDIDATES = (
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
)


class AllGeminiModelsFailed(RuntimeError):
    pass


def get_model_candidates(configured_model: str | None = None) -> list[str]:
    configured = configured_model or os.getenv("GENERATION_MODEL")
    configured_fallbacks = os.getenv("GEMINI_MODEL_FALLBACKS", "")

    candidates: list[str] = []

    if configured:
        candidates.append(configured)

    candidates.extend(
        model.strip()
        for model in configured_fallbacks.split(",")
        if model.strip()
    )
    candidates.extend(DEFAULT_MODEL_CANDIDATES)

    return list(dict.fromkeys(candidates))


def discover_available_models(
    client: genai.Client,
    candidates: Iterable[str] | None = None,
) -> list[str]:
    available: list[str] = []

    for model in candidates or get_model_candidates():
        try:
            client.models.generate_content(
                model=model,
                contents="Reply with exactly: OK",
            )
            available.append(model)
            print(f"Model available: {model}")

        except Exception as exc:
            print(
                f"Model unavailable: {model} "
                f"({type(exc).__name__}: {exc})"
            )

    return available


def generate_with_fallback(
    client: genai.Client,
    contents: str,
    configured_model: str | None = None,
):
    candidates = get_model_candidates(configured_model)
    failures: list[str] = []

    for model in candidates:
        try:
            response = client.models.generate_content(
                model=model,
                contents=contents,
            )
            return response, model

        except errors.APIError as exc:
            failures.append(f"{model}: {exc.code} {exc.status}")
            print(
                f"Generation failed with {model}; trying the next model."
            )

        except Exception as exc:
            failures.append(f"{model}: {type(exc).__name__}: {exc}")
            print(
                f"Generation failed with {model}; trying the next model."
            )

    print("Configured Gemini models failed; checking model availability again.")
    discovered_models = discover_available_models(
        client,
        candidates=get_model_candidates(),
    )

    for model in discovered_models:
        try:
            response = client.models.generate_content(
                model=model,
                contents=contents,
            )
            return response, model

        except Exception as exc:
            failures.append(f"{model}: {type(exc).__name__}: {exc}")
            print(
                f"Retry failed with discovered model {model}."
            )

    details = "; ".join(failures)
    raise AllGeminiModelsFailed(
        "All Gemini model candidates failed. "
        f"Attempts: {details}"
    )
