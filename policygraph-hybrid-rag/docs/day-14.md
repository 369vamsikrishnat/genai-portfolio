# Day 14 — Cost Tracking + Semantic Caching

## Goal

Add cost tracking and Redis-backed semantic caching to the PolicyGraph Hybrid RAG pipeline, then benchmark the impact of caching on latency and generation cost.

## 1. Cost Tracking

Extended:

`src/api/cost_tracker.py`

The `CostTracker` now tracks:

- Total queries
- Input tokens
- Output tokens
- Thinking tokens
- Billed output tokens
- Total cost
- Average cost per query
- Most expensive query

The tracker is thread-safe and provides aggregate statistics through:

    tracker.snapshot()

### Configured Pricing

- Input: `$0.75 / 1M tokens`
- Output: `$3.75 / 1M tokens`

Pricing is configurable through:

    INPUT_PRICE_PER_MILLION
    OUTPUT_PRICE_PER_MILLION

### CostTracker Test

Tested with multiple queries.

Example result:

    Total queries:          2
    Input tokens:        3000
    Output tokens:       1500
    Total cost:      $0.007875
    Average cost:    $0.0039375

The tracker correctly identified the most expensive query.

## 2. Redis Semantic Cache

Created:

`src/api/semantic_cache.py`

The semantic cache stores:

- Query
- Query embedding
- Generated answer
- Metadata
- Creation timestamp

The cache uses cosine similarity rather than exact string matching.

### Cache Configuration

- Backend: Redis
- Similarity method: Cosine similarity
- Similarity threshold: `0.95`
- TTL: `86400` seconds
- TTL: 24 hours

A cache hit occurs when:

    Cosine Similarity >= 0.95

### Cache Metrics

The cache tracks:

- Hits
- Misses
- Total requests
- Hit rate

Statistics are available through:

    cache.stats()

## 3. Redis Setup

Redis was configured using Docker.

    Image:     redis:7
    Container: policygraph-redis
    Port:      6379

The Python Redis client was installed.

Redis connectivity was verified successfully:

    Redis: True

A semantic cache store/retrieve test also succeeded:

    Cosine similarity: 1.0
    Cache hit: True

## 4. Pipeline Integration

Updated:

`src/pipeline.py`

The pipeline now supports:

    run_pipeline(
        query,
        tracker=None,
        use_cache=True,
    )

### Pipeline Flow

    Query
      ↓
    Query Embedding
      ↓
    Semantic Cache Lookup
      ↓
    Dense Retrieval
      ↓
    BM25 Retrieval
      ↓
    RRF
      ↓
    Cross-Encoder Reranking
      ↓
    Gemini Generation
      ↓
    Cost Tracking
      ↓
    Semantic Cache Storage

### Cache Hit

When a sufficiently similar query exists in Redis:

    Query
      ↓
    Query Embedding
      ↓
    Redis Cache Lookup
      ↓
    Cache Hit
      ↓
    Return Cached Answer

A cache hit skips:

- Dense retrieval
- BM25 retrieval
- RRF
- Cross-encoder reranking
- Gemini generation

The query embedding and Redis lookup still occur.

### Cache Miss

    Query
      ↓
    Query Embedding
      ↓
    Cache Miss
      ↓
    Dense Retrieval
      ↓
    BM25
      ↓
    RRF
      ↓
    Cross-Encoder Reranking
      ↓
    Gemini Generation
      ↓
    Cost Tracking
      ↓
    Store Result in Redis

## 5. Gemini Usage and Cost Integration

Updated the pipeline to read Gemini usage metadata.

The pipeline extracts:

    prompt_token_count
    candidates_token_count
    thoughts_token_count

These values are passed to `CostTracker`.

The pipeline therefore tracks:

    Input Tokens
    Output Tokens
    Thinking Tokens
    Billed Output Tokens
    Total Cost
    Average Cost Per Query
    Most Expensive Query

## 6. End-to-End Pipeline Test

Test query:

    What events are covered under Section I for loss or damage to the insured vehicle?

The complete pipeline successfully executed:

    Dense Retrieval
    → BM25
    → RRF
    → Cross-Encoder
    → Gemini
    → CostTracker

### Results

    Retrieved results: 5
    Input tokens:      1,505
    Output tokens:       366
    Thinking tokens:       0
    Cost:          $0.00250125

The generated answer correctly returned the covered events from Section I.

## 7. Cache Benchmark

Created:

`src/evaluation/cache_benchmark.py`

The benchmark executes the same query three times with caching disabled and three times with caching enabled.

It measures:

- Latencies
- Generation costs
- Cache hits
- Cache misses
- Hit rate
- Latency savings
- Cost savings

## 8. Benchmark Without Cache

| Run | Latency | Cost |
|---|---:|---:|
| 1 | 4.6562s | $0.002482 |
| 2 | 4.7314s | $0.002482 |
| 3 | 4.4834s | $0.002482 |
| Average / Total | 4.6237s | $0.007447 |

## 9. Benchmark With Cache

| Run | Latency | Cost | Cache |
|---|---:|---:|---|
| 1 | 4.4259s | $0.002074 | Miss |
| 2 | 0.2219s | $0.000000 | Hit |
| 3 | 0.1296s | $0.000000 | Hit |
| Average / Total | 1.5925s | $0.002074 | |

The first request was a cache miss and generated the answer normally.

The second and third requests were cache hits.

## 10. Cache Benchmark Results

### Cache Statistics

    Hits:        2
    Misses:      1
    Requests:    3
    Hit rate:    66.67%
    Threshold:   0.95
    TTL:         24 hours

### Latency

    Without cache: 4.6237s
    With cache:    1.5925s

    Latency savings: 65.56%

### Cost

    Without cache: $0.007447
    With cache:    $0.002074

    Cost savings: 72.16%

These measurements are specific to the tested repeated-query workload.

## 11. Benchmark Artifacts

Created:

    src/evaluation/cache_benchmark.py
    eval/cache_benchmark_results.json

Updated:

    eval/comparison_results.md

## 12. Files Modified or Created

    src/api/cost_tracker.py
    src/api/semantic_cache.py
    src/pipeline.py
    src/evaluation/cache_benchmark.py
    eval/cache_benchmark_results.json
    eval/comparison_results.md

## 13. Day 14 Checkpoint

- [x] CostTracker extended
- [x] Average cost per query implemented
- [x] Most expensive query tracking implemented
- [x] Gemini token usage connected to CostTracker
- [x] Redis configured with Docker
- [x] Redis Python client installed
- [x] Semantic cache implemented
- [x] Cosine similarity matching implemented
- [x] Similarity threshold configured to `0.95`
- [x] 24-hour TTL configured
- [x] Cache hit/miss tracking implemented
- [x] Pipeline integrated with semantic cache
- [x] Pipeline integrated with CostTracker
- [x] End-to-end pipeline tested
- [x] Cache benchmark implemented
- [x] Cache hit rate measured
- [x] Latency savings measured
- [x] Cost savings measured

## 14. Day 14 Result

The PolicyGraph Hybrid RAG pipeline now includes:

- Gemini cost tracking
- Redis semantic caching
- Query similarity matching
- Cache hit/miss monitoring
- Cache performance benchmarking

### Final Measurements

| Metric | Result |
|---|---:|
| Cache hit rate | 66.67% |
| Latency savings | 65.56% |
| Cost savings | 72.16% |
| Similarity threshold | 0.95 |
| Cache TTL | 24 hours |

The benchmark demonstrated that repeated queries can be served from the semantic cache, reducing both response latency and Gemini generation cost.