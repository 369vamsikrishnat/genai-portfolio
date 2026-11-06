# Similar complaint retrieval evaluation

Source: `F:\ai\genai-portfolio\complaintiq\data\processed` (real_cfpb); embedder `hashing`.

Temporal corpus: 53,883 train documents ending 2025-09-23; 300 sampled queries from strictly later complaints (2025-09-24 to 2026-07-29).

**Relevance is a proxy, not human judgment:** a result is counted relevant when its product and issue match the query complaint. This measures taxonomy similarity, not whether the result is useful precedent or semantically similar.

**Embedding limitation:** The hashing embedder is a deterministic n-gram lexical stand-in, not a semantic embedding model.

Boundary-date test rows excluded: 99; cross-split template queries excluded: 17; duplicate test templates excluded: 32; queries without a training relevance group excluded: 4.

| Mode | Hit@1 | Hit@5 | Hit@10 | P@1 | P@5 | P@10 | MRR@10 | nDCG@5 | nDCG@10 | Search p50 ms | Search p95 ms | Query encode p50 ms | End-to-end p50 ms | End-to-end p95 ms |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| rrf_rerank | 0.377 | 0.683 | 0.807 | 0.377 | 0.357 | 0.338 | 0.513 | 0.360 | 0.346 | 9462.421 | 14489.095 | 1.251 | 9464.004 | 14490.431 |

## Leakage and reproducibility

* The retrieval index contains train-split documents only; queries come from later dates.
* Rows on the shared train/test boundary date and exact normalized template duplicates across the split are excluded.
* The full deterministic query ID list and SHA-256 digest are recorded in the JSON report.
* No genuine relevance judgments are present; do not interpret proxy scores as retrieval accuracy or verified precedent quality.
* BM25 index build time: 6303.811 ms. Dense vectors were precomputed by the artifact build; query embedding latency is reported separately.
