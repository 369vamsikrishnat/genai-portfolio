# ComplaintIQ performance, scalability, and cost evaluation

Artifact: 67,452 records (53,961 training; 13,491 test), 384 dimensions, `hashing`. Hardware: {'platform': 'Windows-10-10.0.19045-SP0', 'processor': 'Intel64 Family 6 Model 142 Stepping 9, GenuineIntel', 'logical_cpus': 4, 'memory_gib': 7.88, 'python': '3.12.0'}.

## Processed-source load throughput

| Requested rows | Loaded rows | seconds | rows/s |
|---:|---:|---:|---:|
| 100 | 100 | 28.4261 | 3.52 |
| 500 | 500 | 23.968 | 20.86 |

## Classification

| Batch rows | p50 ms | p95 ms | p99 ms | rows/s |
|---:|---:|---:|---:|---:|
| 1,000 | 2.167 | 3.681 | 5.013 | 397475.24 |
| 2,500 | 5.461 | 8.52 | 9.077 | 432213.08 |
| 5,000 | 11.118 | 44.61 | 57.903 | 301315.76 |

Single-record classification p50/p95/p99: {'p50': 0.209, 'p95': 0.511, 'p99': 0.735}.

## Retrieval

Dense retrieval is exact NumPy dot product over saved vectors (no ANN index build); query latency includes query encoding for dense/hybrid modes and omits it for BM25.

| Index rows | mode | BM25 build s | p50 ms | p95 ms | p99 ms | queries/s |
|---:|---|---:|---:|---:|---:|---:|
| 1,000 | bm25 | 0.356 | 1.205 | 2.682 | 2.873 | 724.59 |
| 1,000 | dense | 0.356 | 2.144 | 6.377 | 10.805 | 327.71 |
| 1,000 | rrf | 0.356 | 6.755 | 28.579 | 36.318 | 112.58 |
| 1,000 | rrf_rerank | 0.356 | 13.59 | 22.019 | 29.602 | 72.44 |
| 2,500 | bm25 | 1.14 | 1.467 | 6.753 | 9.221 | 412.98 |
| 2,500 | dense | 1.14 | 2.788 | 8.99 | 10.836 | 253.37 |
| 2,500 | rrf | 1.14 | 2.5 | 5.764 | 6.96 | 321.8 |
| 2,500 | rrf_rerank | 1.14 | 19.045 | 32.86 | 46.279 | 48.99 |
| 5,000 | bm25 | 1.625 | 1.968 | 10.482 | 12.04 | 323.22 |
| 5,000 | dense | 1.625 | 7.38 | 17.701 | 19.509 | 123.46 |
| 5,000 | rrf | 1.625 | 6.71 | 27.792 | 42.595 | 90.42 |
| 5,000 | rrf_rerank | 1.625 | 24.595 | 96.777 | 110.965 | 29.0 |

## Quantization

| Rows | Representation | memory MB | recall@10 vs float32 | p50 ms | p95 ms | p99 ms | build s |
|---:|---|---:|---:|---:|---:|---:|---:|
| 1,000 | float32 | 1.46 | 1.0 | 0.234 | 1.115 | 5.198 | 0.0 |
| 1,000 | int8 | 0.37 | 0.964 | 1.947 | 3.775 | 7.086 | 0.032 |
| 1,000 | binary | 0.05 | 0.102 | 0.534 | 1.842 | 2.379 | 0.002 |
| 1,000 | binary+int8_rescore | 0.41 | 0.33 | 0.84 | 4.691 | 6.47 | 0.034 |
| 2,500 | float32 | 3.66 | 1.0 | 0.704 | 1.671 | 3.226 | 0.0 |
| 2,500 | int8 | 0.92 | 0.948 | 4.467 | 8.791 | 11.473 | 0.016 |
| 2,500 | binary | 0.11 | 0.086 | 2.427 | 30.979 | 38.209 | 0.001 |
| 2,500 | binary+int8_rescore | 1.03 | 0.232 | 2.208 | 12.441 | 20.499 | 0.017 |
| 5,000 | float32 | 7.32 | 1.0 | 0.907 | 4.735 | 10.308 | 0.0 |
| 5,000 | int8 | 1.83 | 0.936 | 8.971 | 13.151 | 15.3 | 0.029 |
| 5,000 | binary | 0.23 | 0.076 | 2.51 | 11.654 | 30.022 | 0.005 |
| 5,000 | binary+int8_rescore | 2.06 | 0.264 | 2.87 | 15.568 | 18.993 | 0.033 |

## Monthly replay

Processed 67,452 artifact records across 28 months in 44.1192 s (1528.86 records/s). Monthly batch p50/p95/p99 latency: {'p50': 1554.753, 'p95': 2837.804, 'p99': 3045.59}.

## API and concurrency

Sequential TestClient p50/p95/p99 latency: {'p50': 18.1, 'p95': 46.1, 'p99': 59.94}; throughput: 43.23 requests/s. Statuses: {'200': 10}.

| Workers | Requests | requests/s | p50 ms | p95 ms | p99 ms | statuses |
|---:|---:|---:|---:|---:|---:|---|
| 1 | 10 | 27.23 | 33.536 | 71.51 | 79.781 | {'200': 10} |
| 2 | 20 | 53.39 | 29.249 | 70.764 | 83.594 | {'200': 20} |

## Memory and cost

Process working set before/after: {'working_set_mb': 367.14, 'peak_working_set_mb': 368.36, 'private_bytes_mb': 566.25} / {'working_set_mb': 270.06, 'peak_working_set_mb': 1224.25, 'private_bytes_mb': 611.31} MB (peak: 1224.25 MB). Vector storage estimates (per representation, not aggregate benchmark-process memory): {'float32': 103606272, 'int8': 25901568, 'binary': 3237696}.
Measured external spend: $0.00 (MockLLM; no external provider calls). Mock per-request estimates are not spend. At assumed 94 input / 24 output tokens and configured prices, scenario cost is $0.000160 per escalated triage ($0.1605/1k). The evidence-template draft path makes zero external model calls.

## Limitations

* Benchmark ran on one local laptop, one Python process, and the sampled/deduplicated real artifact; it does not establish production capacity.
* API uses TestClient and MockLLM; network, TLS, remote provider latency, and provider cost are not measured.
* Workload sizes are bounded by the current temporal training index; no out-of-sample extrapolation is reported.
* Process working-set memory is measured, but per-stage peak memory is not isolated.
* Quantization representation sizes estimate deployable vector storage; the benchmark retains float32 and compressed forms simultaneously.
* Quantized recall is top-10 overlap against exact float32 on later holdout queries, not human relevance quality.
