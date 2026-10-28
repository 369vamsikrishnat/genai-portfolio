"""Runtime settings, read from environment variables (prefix CIQ_)."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Settings:
    data_dir: Path
    artifacts_dir: Path
    results_dir: Path
    docs_dir: Path
    embedder: str
    reranker: str
    llm_provider: str  # mock | ollama | gemini
    ollama_url: str
    ollama_model: str
    gemini_model: str
    gemini_api_key: str
    api_key: str  # empty = auth disabled (local dev only)
    rate_limit_per_min: int
    llm_threshold: float  # classifier confidence below this escalates to the LLM
    min_dense_score: float  # below this top-1 cosine the drafter refuses
    price_in_per_m: float  # USD per 1M input tokens, used for the *estimated* cost table
    price_out_per_m: float
    max_chars: int

    @classmethod
    def from_env(cls) -> Settings:
        e = os.getenv
        return cls(
            data_dir=Path(e("CIQ_DATA_DIR", "data")),
            artifacts_dir=Path(e("CIQ_ARTIFACTS_DIR", "artifacts")),
            results_dir=Path(e("CIQ_RESULTS_DIR", "results")),
            docs_dir=Path(e("CIQ_DOCS_DIR", "docs")),
            embedder=e("CIQ_EMBEDDER", "hashing"),
            reranker=e("CIQ_RERANKER", "lexical"),
            llm_provider=e("CIQ_LLM", "mock"),
            ollama_url=e("CIQ_OLLAMA_URL", "http://localhost:11434"),
            ollama_model=e("CIQ_OLLAMA_MODEL", "qwen2.5:7b"),
            gemini_model=e("CIQ_GEMINI_MODEL", "gemini-flash-latest"),
            gemini_api_key=e("GEMINI_API_KEY", ""),
            api_key=e("CIQ_API_KEY", ""),
            rate_limit_per_min=int(e("CIQ_RATE_LIMIT", "60")),
            llm_threshold=float(e("CIQ_LLM_THRESHOLD", "0.70")),
            min_dense_score=float(e("CIQ_MIN_DENSE_SCORE", "0.20")),
            # Placeholder list prices. CHECK the provider's current pricing page and override.
            price_in_per_m=float(e("CIQ_PRICE_IN_PER_M", "0.75")),
            price_out_per_m=float(e("CIQ_PRICE_OUT_PER_M", "3.75")),
            max_chars=int(e("CIQ_MAX_CHARS", "2000")),
        )
