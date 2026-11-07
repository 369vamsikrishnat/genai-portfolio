# Phase 8.4 ? API load test

## Environment
- Local Docker Compose stack.
- Demo configuration: mock LLM, hashing embeddings, lexical reranker.
- API rate limit raised for the benchmark to avoid measuring rate-limit behavior.
- Locust 2.47.0; 30-second headless runs.
- These results describe the local demo stack, not Gemini + MiniLM performance.

## Results

| Concurrent users | Requests | Failures | Throughput (req/s) | Average (ms) | p50 (ms) | p95 (ms) |
|---:|---:|---:|---:|---:|---:|---:|
| 5 | 269 | 0 | 9.73 | 172.45 | 87 | 610 |
| 10 | 265 | 0 | 10.23 | 580.70 | 320 | 2100 |
| 20 | 668 | 0 | 24.37 | 441.60 | 380 | 1100 |

## Interpretation
- All three runs completed with zero request failures.
- Throughput increased to 24.37 requests/second at 20 concurrent users.
- The 10-user run had the highest observed p95 latency (2.1 seconds); the 20-user run's p95 was 1.1 seconds.
- Latency is workload- and run-dependent; these short local tests do not establish production capacity or a sustained service-level objective.

## Scope and limitations
- Each run lasted 30 seconds and used a mixed workload of triage, draft, and health requests.
- The Docker demo stack uses mock/hash/lexical components. These figures must not be presented as Gemini + MiniLM benchmarks.
- Results are local measurements, not a production deployment or external load test.
