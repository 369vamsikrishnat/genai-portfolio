# Evidence-grounded response generation evaluation

Source: `F:\ai\genai-portfolio\complaintiq\data\processed` (real_cfpb).
Train-only index: 53,883 records through 2025-09-23; evaluated 50 later complaints from 2025-09-24 to 2026-07-29.

## Automated checks

* Draft statuses: {'ok': 49, 'refused': 1}.
* Citation coverage among successful drafts: 1.0.
* All retrieved precedents cited: 1.0.
* Exact evidence-template validation: 1.0.
* Unsupported factual fields detected: 0.
* Model generation calls: 0.

Final text is a deterministic template containing only retrieved complaint IDs, product, issue, and historical response-category metadata. Exact-template validation checks the emitted text against those retrieved fields; it is not semantic entailment.

Historical company response categories are quoted as reported metadata only. They are not presented as correct, legally approved, or applicable to the current complaint.

## Human-judged quality

No human review study was run; politeness, usefulness, and legal suitability are unmeasured.

This automated report does not measure empathy, usefulness, factual entailment beyond the structured evidence fields, or legal suitability. Every draft still requires human review.

## Reproducibility

* Seed: 7; query count: 50; query ID SHA-256: `d8d760e8c4f5805ac45ae78f4b87d0464378e8c1f8e32f9a37b209a2a555d47b`.
* Boundary-date rows excluded: 99; cross-split template queries excluded: 17; duplicate test templates excluded: 32.
* Train BM25 index build: 10776.303 ms; draft pipeline p50/p95: 23.726 / 60.638 ms.
