"""Rule-based regulatory/severity flags. Validate against YOUR hand-labelled sheet (evals/risk.py)."""
from __future__ import annotations

import re

RULES: dict[str, list[str]] = {
    "legal_threat": [r"\battorney\b", r"\blawsuit\b", r"\bsue\b", r"\bcourt\b"],
    "regulator_mention": [r"\bcfpb\b", r"\bocc\b", r"\battorney general\b", r"\bregulator"],
    "identity_theft_fraud": [r"identity theft", r"\bfraud", r"unauthorized", r"\bstolen\b"],
    "foreclosure_housing": [r"foreclos", r"\beviction\b", r"lose my home"],
    "vulnerable_consumer": [r"\belderly\b", r"\bveteran\b", r"\bmilitary\b", r"\bdisabled\b"],
    "discrimination": [r"discriminat", r"\bracial", r"\bunfair treatment\b"],
}
_C = {k: [re.compile(p, re.I) for p in v] for k, v in RULES.items()}


def risk_flags(text: str) -> list[str]:
    return [k for k, rxs in _C.items() if any(rx.search(text) for rx in rxs)]
