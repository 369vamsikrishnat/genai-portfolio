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
    """Gemini REST API (free tier works with an AI Studio key). Free-tier limits are tight and
    change often: this client backs off on 429, but plan batch work around Ollama instead."""

    def __init__(self, model: str, api_key: str):
        if not api_key:
            raise ValueError("set GEMINI_API_KEY (create one in Google AI Studio)")
        self.name, self.model, self.key = f"gemini:{model}", model, api_key

    def generate(self, prompt: str, max_tokens: int = 256) -> LLMResponse:
        t0 = time.perf_counter()
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        r = _post_with_retry(url, headers={"x-goog-api-key": self.key}, json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0, "maxOutputTokens": max_tokens}}).json()
        try:
            text = r["candidates"][0]["content"]["parts"][0]["text"].strip()
        except (KeyError, IndexError):
            text = ""
        meta = r.get("usageMetadata", {})
        u = Usage(meta.get("promptTokenCount", estimate_tokens(prompt)),
                  meta.get("candidatesTokenCount", estimate_tokens(text)))
        return LLMResponse(text, u, (time.perf_counter() - t0) * 1000)


def get_llm(settings, truth: dict[str, str] | None = None):
    p = settings.llm_provider
    if p == "mock":
        return MockLLM(truth=truth)
    if p == "ollama":
        return OllamaClient(settings.ollama_model, settings.ollama_url)
    if p == "gemini":
        return GeminiClient(settings.gemini_model, settings.gemini_api_key)
    raise ValueError(f"unknown CIQ_LLM provider: {p}")
