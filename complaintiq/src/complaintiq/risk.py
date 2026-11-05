
"""Context-aware risk flags aligned with the frozen ComplaintIQ risk definition."""
from __future__ import annotations

import re

RULES: dict[str, list[str]] = {
    "legal_threat": [
        r"\b(?:i will|i intend to|i plan to|i am prepared to|i am going to)"
        r"\s+(?:pursue|take|initiate|commence|bring)\s+"
        r"(?:legal action|action to sue|litigation|a lawsuit|legal proceedings)\b",
        r"\b(?:if|unless)\b.{0,100}\b(?:i will|i intend to|i plan to)"
        r".{0,60}\b(?:sue|pursue legal action|take legal action|file a lawsuit)\b",
        r"\b(?:i will|i intend to|i plan to|i am going to)"
        r"\s+(?:hire|retain|engage)\s+(?:an?\s+)?attorney\b",
        r"\b(?:i will|i intend to|i plan to)"
        r"\s+(?:contact|consult|speak with)\s+(?:my|an?)\s+attorney\b",
        r"\b(?:will seek litigation|seek litigation if|before taking legal action|"
        r"prepared to take legal action|will take action to sue)\b",
        r"\b(?:demand|filed|filing|commencing|commenced)\s+"
        r"(?:for\s+)?arbitration\b",
    ],
    "regulator_mention": [
        r"\b(?:i will|i intend to|i plan to|i am going to|unless.{0,50}i will)"
        r".{0,80}\b(?:report|refer|file a complaint|escalate)\b"
        r".{0,80}\b(?:occ|attorney general|state agency|regulator|regulatory agency|ftc|federal agency)\b",
        r"\b(?:i will|i intend to|i plan to)"
        r".{0,80}\b(?:notify|contact)\b.{0,60}\b(?:attorney general|regulator|occ|ftc)\b",
    ],
    "identity_theft_fraud": [
        r"\b(?:someone|another person|a third party|an unknown person)"
        r".{0,100}\b(?:opened|created|used|took over|accessed|stole)\b"
        r".{0,100}\b(?:account|card|funds|money|identity|personal information)\b",
        r"\b(?:i am|i'm|iam)\s+(?:a\s+)?victim of identity theft\b",
        r"\bidentity theft\b.{0,120}\b(?:account|loan|credit card|funds|money|transaction|opened|taken|used|harm)\b",
        r"\b(?:identity was stolen|identity has been stolen)\b",
        r"\bidentity theft\b.{0,500}\b(?:account|loan|credit card|collections?)\b.{0,100}\bopened\b",
        r"\b(?:account|loan|credit card|collection)\b.{0,100}\bopened\b.{0,100}\b(?:in my name|without my knowledge|without my consent)\b",
        r"\b(?:someone|another person|third party)\b.{0,100}\b(?:opened|created|took out)\b.{0,100}\b(?:account|loan|card)\b",
        r"\b(?:fraudulent|unauthorized)\s+(?:withdrawal|transfer|charge|transaction|purchase)\b",
        r"\b(?:unauthorized|fraudulent)\s+(?:charge|transaction|withdrawal|transfer)\b"
        r".{0,100}\b(?:i did not make|i did not authorize|not made or authorized by me)\b",
        r"\b(?:account takeover|took over my account|stole my funds|stole my money)\b",
        r"\b(?:i did not make|i did not authorize|not made or authorized by me)"
        r".{0,100}\b(?:charge|transaction|withdrawal|transfer|purchase)\b",
        r"\b(?:fraud|scam)\b.{0,100}\b(?:charged|debited|took|stole|transferred)\b"
        r".{0,80}\b(?:money|funds|account|card|\$\s?\d)\b",
    ],
    "foreclosure_housing": [
        r"\b(?:eviction notice|notice of eviction|notice to vacate|lockout notice)\b",
        r"\bnotice of default\b",
        r"\bnotice of intent to foreclose\b",
        r"\bforeclosure notice\b",
        r"\bforeclosure (?:filing|lawsuit|sale date|auction date|sale scheduled)\b",
        r"\b(?:scheduled|set|notice of)\s+(?:foreclosure )?(?:sale|auction)\b",
        r"\b(?:sheriff|court)-ordered eviction\b",
        r"\b(?:eviction|foreclosure)\b.{0,80}\b(?:deadline|by [A-Z][a-z]+ \d{1,2}|sale date|lockout)\b",
    ],
    "vulnerable_consumer": [
        r"\b(?:elderly|senior citizen|veteran|servicemember|service member|disabled|disability)\b"
        r".{0,250}\b(?:lost|loss|stolen|fraud|debit|withdrawal|funds|money|benefits|"
        r"account closed|denied|charged|financial harm|exploited)\b",
        r"\b(?:lost|loss|stolen|fraud|debit|withdrawal|funds|money|benefits|"
        r"account closed|denied|charged|financial harm|exploited)\b"
        r".{0,250}\b(?:elderly|senior citizen|veteran|servicemember|service member|disabled|disability)\b",
    ],
    "discrimination": [
        r"\b(?:racial|age|gender|disability|religious)\s+discrimination\b",
        r"\b(?:discriminated against|discriminatory treatment|discrimination against me)\b",
        r"\btreated differently\b.{0,100}\b(?:race|age|gender|disability|religion)\b",
    ],
    "missed_statutory_deadline": [
        r"\b(?:statutory|legal|law-required|legally required)\b"
        r".{0,100}\b(?:30|thirty|60|sixty|10|ten|5|five)\s*[- ]day\b"
        r".{0,160}\b(?:no response|not responded|still outstanding|failed to respond|"
        r"not investigated|investigation remains pending|provisional credit|"
        r"not received|remains unresolved)\b",
        r"\b(?:30|thirty|60|sixty|10|ten|5|five)\s*[- ]day\b"
        r".{0,100}\b(?:statutory|legal|law-required)\s+(?:deadline|limit|requirement)\b"
        r".{0,160}\b(?:no response|still outstanding|not investigated|pending|"
        r"not received|remains unresolved)\b",
        r"\b(?:required by law|by law|legal timeframe|statutory deadline)\b"
        r".{0,120}\b(?:overdue|passed|exceeded|failed|not received|still outstanding)\b",
    ],
}

_COMPILED = {
    name: [re.compile(pattern, re.I | re.S) for pattern in patterns]
    for name, patterns in RULES.items()
}


def risk_matches(text: str) -> dict[str, list[str]]:
    """Return qualifying contextual evidence for each risk category."""
    if not isinstance(text, str) or not text.strip():
        return {}

    matches: dict[str, list[str]] = {}
    for flag, patterns in _COMPILED.items():
        evidence = []
        for pattern in patterns:
            for match in pattern.finditer(text):
                snippet = match.group(0).strip()
                if snippet and snippet not in evidence:
                    evidence.append(snippet)
        if evidence:
            matches[flag] = evidence

    return matches


def risk_flags(text: str) -> list[str]:
    """Return risk category names; preserve the existing public API."""
    return list(risk_matches(text))
