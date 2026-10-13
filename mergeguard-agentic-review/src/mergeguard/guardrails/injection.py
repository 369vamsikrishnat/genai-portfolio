from __future__ import annotations

import re
import unicodedata

INJECTION_PATTERNS = (
    re.compile(r"\bignore\s+(?:(?:all|previous|prior)\s+)?instructions?\b"),
    re.compile(r"\bapprove\s+(?:(?:this|the)\s+)?pr\b"),
    re.compile(r"\byou\s+are\s+now\b"),
    re.compile(r"\bsystem\s+prompt\b"),
    re.compile(r"\bdisregard\b(?:\s+(?:all|previous|prior|the))?(?:\s+instructions?)?\b"),
    re.compile(r"\bforget\s+(?:(?:all|previous|prior)\s+)?instructions?\b"),
    re.compile(r"\boverride\s+(?:the\s+)?(?:system|review|safety|developer)\b"),
    re.compile(r"\bbypass\s+(?:all\s+)?(?:checks|review|safeguards)\b"),
    re.compile(r"\breveal\s+(?:the\s+)?(?:system\s+)?prompt\b"),
    re.compile(r"\bact\s+as\s+(?:an?\s+)?(?:unrestricted|different|new)\b"),
)


def detect_prompt_injection(texts: dict[str, str]) -> list[str]:
    flagged_sources: list[str] = []
    for source, text in texts.items():
        normalized = unicodedata.normalize("NFKC", text).casefold()
        normalized = re.sub(r"\s+", " ", normalized).strip()
        if any(pattern.search(normalized) for pattern in INJECTION_PATTERNS):
            flagged_sources.append(source)
    return flagged_sources