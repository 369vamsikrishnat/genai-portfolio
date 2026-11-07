"""LLM clients behind one interface: mock (tests/demo), Ollama (local, free), Gemini (free tier)."""
from __future__ import annotations

import random
import re
import time
from dataclasses import dataclass

import requests


@dataclass
class Usage:
    prompt_tokens: int = 0
    completion_tokens: int = 0


@dataclass
class LLMResponse:
    text: str
    usage: Usage
    latency_ms: float = 0.0


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def cost_usd(usage: Usage, price_in_per_m: float, price_out_per_m: float) -> float:
    return (usage.prompt_tokens * price_in_per_m + usage.completion_tokens * price_out_per_m) / 1e6


def _post_with_retry(url: str, retries: int = 4, **kw) -> requests.Response:
    for attempt in range(retries):
        r = requests.post(url, timeout=120, **kw)
        if r.status_code in (429, 500, 502, 503) and attempt < retries - 1:
            time.sleep(2 ** attempt)
            continue
        r.raise_for_status()
        return r
    raise RuntimeError("unreachable")


class MockLLM:
    """Offline stand-in. For classification it can SIMULATE an LLM of a given accuracy using a
    ground-truth lookup; this is only for tests and demos. Numbers from it are not results."""

    name = "mock"

    def __init__(self, truth: dict[str, str] | None = None, accuracy: float = 0.9, seed: int = 0):
        self.truth, self.accuracy, self.rng = truth or {}, accuracy, random.Random(seed)

    def generate(self, prompt: str, max_tokens: int = 256) -> LLMResponse:
        t0 = time.perf_counter()
        if "TASK: CLASSIFY" in prompt:
            labels = re.findall(r"^- (.+)$", prompt.split("LABELS:")[1].split("COMPLAINT:")[0], re.M)
            text = prompt.split("<complaint>")[1].split("</complaint>")[0].strip()
            gold = self.truth.get(text)
            if gold in labels and self.rng.random() < self.accuracy:
                out = gold
            else:
                out = self.rng.choice(labels)
        elif "TASK: DRAFT" in prompt:
            ids = re.findall(r"\[CFPB-\d+\]", prompt.split("PRECEDENTS:")[1].split("COMPLAINT:")[0])
            cites = " ".join(dict.fromkeys(ids[:2]))
            out = ("Thank you for contacting us. We understand your concern and have opened a review. "
                   f"In similar cases {cites} the matter was reviewed and the outcome was documented. "
                   "A specialist will follow up within the regulatory deadline.")
        elif "TASK: BRIEF" in prompt:
            out = "Complaint volume for this issue rose sharply versus its recent baseline; review recommended."
        else:
            out = "OK"
        u = Usage(estimate_tokens(prompt), estimate_tokens(out))
        return LLMResponse(out, u, (time.perf_counter() - t0) * 1000)


class OllamaClient:
    def __init__(self, model: str = "qwen2.5:7b", url: str = "http://localhost:11434"):
        self.name, self.url = f"ollama:{model}", url.rstrip("/")
        self.model = model

    def generate(self, prompt: str, max_tokens: int = 256) -> LLMResponse:
        t0 = time.perf_counter()
        r = _post_with_retry(f"{self.url}/api/generate", json={
            "model": self.model, "prompt": prompt, "stream": False,
            "options": {"temperature": 0, "num_predict": max_tokens}}).json()
        u = Usage(r.get("prompt_eval_count", estimate_tokens(prompt)),
                  r.get("eval_count", estimate_tokens(r.get("response", ""))))
        return LLMResponse(r.get("response", "").strip(), u, (time.perf_counter() - t0) * 1000)


class GeminiClient:
    """Gemini REST client with live Flash-model discovery and automatic failover."""

    CATALOG_URL = "https://generativelanguage.googleapis.com/v1beta/models"
    TRANSIENT_STATUSES = {429, 500, 502, 503, 504}

    def __init__(self, model: str, api_key: str):
        if not api_key:
            raise ValueError("set GEMINI_API_KEY (create one in Google AI Studio)")
        self.name = f"gemini:{model}"
        self.model = model
        self.key = api_key
        self.models_used: set[str] = set()
        self.retry_wait = 5
        self.max_wait = 60
        self.max_retry_cycles = 4

    def _discover_models(self) -> list[str]:
        """Fetch models supported by this API key; keep Flash models only."""
        models: list[str] = []
        page_token = None

        while True:
            params = {"pageSize": 1000}
            if page_token:
                params["pageToken"] = page_token

            response = requests.get(
                self.CATALOG_URL,
                headers={"x-goog-api-key": self.key},
                params=params,
                timeout=30,
            )
            response.raise_for_status()
            payload = response.json()

            for item in payload.get("models", []):
                methods = item.get("supportedGenerationMethods", [])
                name = item.get("name", "")
                model_id = name.removeprefix("models/")
                model_lower = model_id.lower()
                excluded = ("tts", "image", "audio", "live")
                if (
                    "generateContent" in methods
                    and "flash" in model_lower
                    and not any(term in model_lower for term in excluded)
                    and model_id
                ):
                    models.append(model_id)

            page_token = payload.get("nextPageToken")
            if not page_token:
                break

        # Try the configured model first, then other discovered Flash models.
        ordered = []
        if self.model in models:
            ordered.append(self.model)
        ordered.extend(sorted(m for m in set(models) if m not in ordered))
        return ordered

    def generate(self, prompt: str, max_tokens: int = 256) -> LLMResponse:
        started = time.perf_counter()
        wait_seconds = self.retry_wait
        last_error = None

        for cycle in range(1, self.max_retry_cycles + 1):
            try:
                candidates = self._discover_models()
            except requests.HTTPError as error:
                status = error.response.status_code if error.response is not None else None
                if status not in self.TRANSIENT_STATUSES:
                    raise RuntimeError(
                        f"Gemini model discovery failed permanently (HTTP {status}). "
                        "Check API key, permissions, and API access."
                    ) from error
                last_error = error
                candidates = []
            except requests.RequestException as error:
                last_error = error
                candidates = []

            if candidates:
                for model_id in candidates:
                    url = f"{self.CATALOG_URL}/{model_id}:generateContent"
                    try:
                        response = requests.post(
                            url,
                            headers={"x-goog-api-key": self.key},
                            json={
                                "contents": [{"parts": [{"text": prompt}]}],
                                "generationConfig": {
                                    "temperature": 0,
                                    "maxOutputTokens": max_tokens,
                                },
                            },
                            timeout=120,
                        )
                        response.raise_for_status()
                        payload = response.json()
                        parts = (
                            payload.get("candidates", [{}])[0]
                            .get("content", {})
                            .get("parts", [])
                        )
                        text = "".join(
                            part.get("text", "") for part in parts
                        ).strip()

                        if not text:
                            last_error = RuntimeError(
                                f"{model_id} returned an empty response"
                            )
                            continue

                        usage = payload.get("usageMetadata", {})
                        tokens = Usage(
                            usage.get("promptTokenCount", estimate_tokens(prompt)),
                            usage.get("candidatesTokenCount", estimate_tokens(text)),
                        )
                        self.model = model_id
                        self.name = f"gemini:{model_id}"
                        self.models_used.add(model_id)
                        return LLMResponse(
                            text,
                            tokens,
                            (time.perf_counter() - started) * 1000,
                        )

                    except requests.HTTPError as error:
                        status = (
                            error.response.status_code
                            if error.response is not None
                            else None
                        )
                        if status in (401, 403):
                            raise RuntimeError(
                                f"Gemini request rejected (HTTP {status}). "
                                "Check the API key and permissions."
                            ) from error
                        last_error = error
                    except (requests.RequestException, ValueError, KeyError, IndexError) as error:
                        last_error = error

            if cycle < self.max_retry_cycles:
                time.sleep(wait_seconds)
                wait_seconds = min(wait_seconds * 2, self.max_wait)

        detail = (
            f"{type(last_error).__name__}: {last_error}"
            if last_error is not None
            else "no usable Flash models were returned"
        )
        raise RuntimeError(
            f"Gemini failed after {self.max_retry_cycles} discovery/failover cycles; "
            f"last error: {detail}. Completed evaluation batches remain checkpointed."
        ) from last_error

def get_llm(settings, truth: dict[str, str] | None = None):
    p = settings.llm_provider
    if p == "mock":
        return MockLLM(truth=truth)
    if p == "ollama":
        return OllamaClient(settings.ollama_model, settings.ollama_url)
    if p == "gemini":
        return GeminiClient(settings.gemini_model, settings.gemini_api_key)
    raise ValueError(f"unknown CIQ_LLM provider: {p}")
