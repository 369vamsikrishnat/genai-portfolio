# Retrieval Comparison — Day 13

## Retrieval Ablation

| Configuration | Recall@5 | Hit@1 | Hit@3 | Hit@5 | MRR |
|---|---:|---:|---:|---:|---:|
| Dense Only | 76.60% | 59.57% | 74.47% | 76.60% | 67.66% |
| Dense + BM25 + RRF | 80.85% | 63.83% | 76.60% | 80.85% | 71.31% |
| Dense + BM25 + RRF + Reranker | 74.47% | 74.47% | 74.47% | 74.47% | 74.47% |

## Chunking Ablation

| Chunking Strategy | Recall@5 | Hit@1 | Hit@3 | Hit@5 | MRR |
|---|---:|---:|---:|---:|---:|
| Section-Aware | 95.74% | 82.98% | 91.49% | 95.74% | 88.40% |
| Fixed-Size | 76.60% | 63.83% | 74.47% | 76.60% | 70.00% |

## Evaluation Set

- Total golden-set cases: 50
- Answerable cases: 47
- Abstention cases: 3

## Notes

The retrieval ablation compares the contribution of different retrieval stages.

The chunking ablation compares section-aware chunking with fixed-size chunking while keeping dense retrieval and the evaluation set consistent.

The results are specific to the current golden set and policy document.
## Day 14 — Semantic Cache Benchmark

### Benchmark Configuration

- Query: `What events are covered under Section I for loss or damage to the insured vehicle?`
- Repetitions: 3
- Semantic similarity threshold: 0.95
- Cache TTL: 86400 seconds

### Cost and Latency

| Configuration | Avg Latency | Total Cost |
|---|---:|---:|
| Without Cache | 4.6237s | $0.007447 |
| With Cache | 1.5925s | $0.002074 |

### Cache Performance

| Metric | Result |
|---|---:|
| Cache Hits | 2 |
| Cache Misses | 1 |
| Total Cache Requests | 3 |
| Cache Hit Rate | 66.67% |
| Latency Savings | 65.56% |
| Cost Savings | 72.16% |

### Notes

The benchmark repeats the same query multiple times.

Without cache, every request executes the full retrieval and generation pipeline.

With cache, the first request populates Redis and subsequent semantically equivalent requests can return the cached answer without executing the retrieval, reranking, or generation stages.

The measured results are specific to this benchmark query, repetition count, model configuration, and local environment.
