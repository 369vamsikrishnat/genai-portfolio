# Complaint retrieval ablation

## Evaluation setup

- Source: real CFPB complaints; temporal train-only index with 53,883 deduplicated documents.
- Training data ends: 2025-09-23; held-out queries: 2025-09-24 to 2026-07-29.
- Queries: 300; seed: 0; k: 10.
- Query ID SHA256: `413e5f547dc79773d2877e1f6eda634a909b0e63eda9ed4ccc17d484394f8faa`; cross-encoder used the identical query sample.
- Dense retrieval uses the hashing embedder, a deterministic lexical stand-in rather than a semantic embedding model.
- Automated relevance is a weak product/issue-match proxy, not a measure of verified precedent usefulness.

## Retrieval results

| Mode | Hit@1 | Hit@5 | Hit@10 | P@5 | P@10 | MRR@10 | nDCG@10 | Search p50 ms | Search p95 ms |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| BM25 | 0.4067 | 0.6967 | 0.8267 | 0.3413 | 0.3353 | 0.5306 | 0.3445 | 3.340 | 9.431 |
| Dense | 0.2733 | 0.5100 | 0.6033 | 0.2600 | 0.2523 | 0.3701 | 0.2559 | 10.203 | 16.895 |
| RRF | 0.3733 | 0.6667 | 0.7700 | 0.3200 | 0.3030 | 0.5000 | 0.3154 | 13.711 | 22.386 |
| RRF + cross-encoder | 0.3767 | 0.6833 | 0.8067 | 0.3567 | 0.3377 | 0.5126 | 0.3458 | 9462.421 | 14489.095 |

## Human top-1 relevance review

- Reviewed: 50 RRF query-to-top-1 pairs.
- Relevant: 36; not relevant: 10; uncertain: 4.
- Relevance among decisive judgments: **78.26% (36/46)**.
- Copilot assisted the narrative judgments. This is not independent expert validation.
- Relevant pairs commonly shared the underlying dispute; irrelevant pairs often shared only broad labels. Uncertain cases had limited detail or partial overlap.

## Decision

- BM25 is the strongest non-reranked baseline on the weak proxy metrics and has the lowest search latency.
- The cross-encoder produces the strongest proxy ranking metrics: Hit@10 and nDCG@10 improve over RRF.
- However, cross-encoder search p50 is 9462.421 ms versus 13.711 ms for RRF, approximately 690.1x slower.

**Practical winner: RRF as the CPU retrieval default**, retaining the cross-encoder as an optional reranking experiment when latency is acceptable. BM25 remains a strong low-latency baseline.

## Leakage, reproducibility and limitations

- The index uses training-period documents only; queries are from strictly later dates.
- Boundary-date rows excluded: 99; cross-split template queries excluded: 17; duplicate test templates excluded: 32.
- Exact normalized narrative duplicates are excluded across the train/query boundary.
- Product/issue proxy relevance measures taxonomy agreement, not semantic similarity or precedent usefulness.
- The 50-pair human review is a small Copilot-assisted sample and must not be generalized as a full-corpus relevance score.
- Latencies reflect this CPU environment, not production or GPU hardware.

## Supporting artifacts

- Baseline metrics: `results/retrieval_ablation.json`
- Cross-encoder metrics: `results/retrieval_rerank_v1.json`
- Cross-encoder comparison: `docs/retrieval_cross_encoder_ablation.md`
- Human review report: `docs/retrieval_human_review_v1.md`
- Reviewed pairs: `results/retrieval_top1_review_50_v1_reviewed.csv`
