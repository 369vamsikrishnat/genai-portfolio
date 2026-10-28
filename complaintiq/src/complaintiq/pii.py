"""Regex PII redaction. Patterns are RE2-compatible so the same list runs in Python and DuckDB.

CFPB already masks many identifiers with XXXX; this is defence in depth, not a guarantee.
For stronger coverage plug Microsoft Presidio in behind `redact()`.
"""
from __future__ import annotations

import re

PATTERNS: list[tuple[str, str, str]] = [
    ("ssn", r"\b\d{3}-\d{2}-\d{4}\b", "[SSN]"),
    ("card", r"\b(?:\d[ -]?){13,16}\b", "[CARD]"),
    ("email", r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "[EMAIL]"),
    ("phone", r"(?:\+?1[ .-]?)?(?:\(\d{3}\)|\b\d{3})[ .-]?\d{3}[ .-]?\d{4}\b", "[PHONE]"),
    ("number", r"\b\d{9,}\b", "[NUMBER]"),
]
_COMPILED = [(n, re.compile(p), t) for n, p, t in PATTERNS]


def redact(text: str) -> tuple[str, dict[str, int]]:
    counts: dict[str, int] = {}
    for name, rx, token in _COMPILED:
        text, n = rx.subn(token, text)
        if n:
            counts[name] = n
    return text, counts


def redact_text(text: str) -> str:
    return redact(text)[0]


def sql_redact_expr(column: str) -> str:
    """Nested regexp_replace(...) expression for DuckDB."""
    expr = column
    for _, pattern, token in PATTERNS:
        expr = f"regexp_replace({expr}, '{pattern}', '{token}', 'g')"
    return expr
