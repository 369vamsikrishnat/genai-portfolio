# Similar complaint retrieval evaluation

Source: `F:\ai\genai-portfolio\complaintiq\data\processed` (real_cfpb); embedder `hashing`.

Temporal corpus: 53,883 train documents ending 2025-09-23; 300 sampled queries from strictly later complaints (2025-09-24 to 2026-07-29).

**Relevance is a proxy, not human judgment:** a result is counted relevant when its product and issue match the query complaint. This measures taxonomy similarity, not whether the result is useful precedent or semantically similar.

**Embedding limitation:** The hashing embedder is a deterministic n-gram lexical stand-in, not a semantic embedding model.

Boundary-date test rows excluded: 99; cross-split template queries excluded: 17; duplicate test templates excluded: 32; queries without a training relevance group excluded: 4.

| Mode | Hit@1 | Hit@5 | Hit@10 | P@1 | P@5 | P@10 | MRR@10 | nDCG@5 | nDCG@10 | Search p50 ms | Search p95 ms | Query encode p50 ms | End-to-end p50 ms | End-to-end p95 ms |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| bm25 | 0.407 | 0.697 | 0.827 | 0.407 | 0.341 | 0.335 | 0.531 | 0.353 | 0.344 | 3.34 | 9.431 | 0.0 | 3.34 | 9.431 |
| dense | 0.273 | 0.510 | 0.603 | 0.273 | 0.260 | 0.252 | 0.370 | 0.262 | 0.256 | 10.203 | 16.895 | 1.301 | 11.709 | 20.085 |
| rrf | 0.373 | 0.667 | 0.770 | 0.373 | 0.320 | 0.303 | 0.500 | 0.332 | 0.315 | 13.711 | 22.386 | 1.51 | 15.386 | 27.212 |

## Leakage and reproducibility

* The retrieval index contains train-split documents only; queries come from later dates.
* Rows on the shared train/test boundary date and exact normalized template duplicates across the split are excluded.
* The full deterministic query ID list and SHA-256 digest are recorded in the JSON report.
* No genuine relevance judgments are present; do not interpret proxy scores as retrieval accuracy or verified precedent quality.
* BM25 index build time: 10559.441 ms. Dense vectors were precomputed by the artifact build; query embedding latency is reported separately.
