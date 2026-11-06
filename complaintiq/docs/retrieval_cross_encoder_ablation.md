# Retrieval cross-encoder ablation

## Experimental controls

- Same temporal train-only, template-deduplicated index and held-out query sample as baseline.
- Queries: 300; seed: 0.
- Query ID SHA256: `413e5f547dc79773d2877e1f6eda634a909b0e63eda9ed4ccc17d484394f8faa` (identical to baseline).
- Candidate pool: RRF top 50; cross-encoder: `cross-encoder/ms-marco-MiniLM-L-6-v2`.
- Relevance is a weak product/issue-match proxy, not human-judged precedent relevance.
- Baseline: `results/retrieval_ablation.json`; reranker: `results/retrieval_rerank_v1.json`.

## Results

| Metric | RRF | RRF + cross-encoder |
|---|---:|---:|
| Hit@1 | 0.3733 | 0.3767 |
| Hit@5 | 0.6667 | 0.6833 |
| Hit@10 | 0.7700 | 0.8067 |
| P@5 | 0.3200 | 0.3567 |
| P@10 | 0.3030 | 0.3377 |
| MRR@10 | 0.5000 | 0.5126 |
| nDCG@5 | 0.3317 | 0.3599 |
| nDCG@10 | 0.3154 | 0.3458 |
| Search p50 (ms) | 13.711 | 9462.421 |
| Search p95 (ms) | 22.386 | 14489.095 |
| End-to-end p50 (ms) | 15.386 | 9464.004 |
| End-to-end p95 (ms) | 27.212 | 14490.431 |

## Decision

The cross-encoder improves Hit@10 by 3.67 percentage points and nDCG@10 by 0.0304. Search p50 rises from 13.711 ms to 9462.421 ms (690.1x).

**Decision: retain RRF as the practical CPU retrieval default.** The cross-encoder remains an optional quality/latency trade-off.

## Limitations

- Product/issue agreement is a weak taxonomy proxy, not verified precedent relevance.
- The baseline uses a hashing lexical stand-in for dense embeddings.
- Latency reflects this CPU environment, not GPU or production hardware.
- This experiment uses 300 queries, without human-judged relevance labels.
