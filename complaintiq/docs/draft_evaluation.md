# ComplaintIQ Draft Evaluation

## 50-complaint evaluation

- Evaluation sample: 50 later-in-time complaints, seed 7.
- Evaluation period: 2025-09-24 to 2026-07-29.
- Training/index cutoff: 2025-09-23.
- Successful drafts: 49.
- Refused drafts: 1.
- Citation coverage among successful drafts: 100%.
- Retrieved precedents cited: 100%.
- Exact evidence-template validation: 100%.
- Unsupported factual fields detected: 0.
- LLM generation calls: 0.
- Draft latency p50: 23.726 ms.
- Draft latency p95: 60.638 ms.

The evaluation used a temporal split and a fixed sample (seed 7). These metrics measure retrieval/output structure and template integrity, not semantic correctness or customer usefulness. Human-judged quality, politeness, legal suitability, and usefulness were not measured.

## Precedent relevance review

Assistant-assisted rubric review covered 30 successful drafts and 150 retrieved precedents.

| Relevance rating | Count | Share |
|---|---:|---:|
| Strongly relevant (3) | 83 | 55.3% |
| Partially relevant (2) | 35 | 23.3% |
| Irrelevant (1) | 32 | 21.3% |
| **Total** | **150** | **100%** |

- Mean relevance: 2.340 / 3.
- Drafts with at least one strongly relevant precedent: 29 / 30.
- Review type: assistant-assisted ratings, not independent human validation.
- No inter-rater reliability or independent annotator agreement was measured.

These ratings are a preliminary relevance review, not a validated human quality study. The worksheet is `results/draft_relevance_review.csv`.

## Drafter implementation

The current drafter is deterministic and template-generated, not model-generated. It renders retrieved historical CFPB metadata into a fixed evidence template. The LLM is not called by the draft path. The existence of prompt-building code does not mean that prompt is used to generate responses.

The template identifies historical records as context only, avoids claiming their outcomes apply to the current complaint, and requires human review before a substantive response is sent.

## Guardrails

Five focused checks passed: prompt-injection blocking, input sanitization, insufficient-evidence refusal, citation/historical-context validation, and rejection of unsupported modified prose. Details are in `docs/guardrail_checks.md`.

## Limitations

- Exact-template validation is not semantic entailment.
- Retrieval relevance ratings were assistant-assisted, not independently human-rated.
- The evaluation did not measure human-perceived response quality or legal suitability.
- The drafter does not generate personalized substantive replies; it produces a deterministic evidence summary for human review.
