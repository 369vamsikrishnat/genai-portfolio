# Scale and quantization evaluation

## Real-vector quantization benchmark

Measured against the real CFPB MiniLM artifact `complaintiq_full_minilm`.

| Setting | Value |
|---|---:|
| Embedding dimension | 384 |
| Training index | 25,000 vectors |
| Query set | 50 later-period temporal holdout vectors |
| Training cutoff | 2025-09-23 |
| Holdout starts | 2025-09-24 |
| Neighbors | 10 |
| Benchmark runtime | 7.6 seconds |
| Search baseline | Exact float32 dot-product top-k |

### Results

| Representation | Stored vector memory | Recall@10 vs float32 | p50 ms | p95 ms | p99 ms | Build s |
|---|---:|---:|---:|---:|---:|---:|
| float32 exact | 36.62 MB | 1.000 | 6.125 | 89.278 | 605.797 | 0.000 |
| int8 | 9.16 MB | 0.982 | 79.384 | 146.914 | 176.985 | 0.231 |
| binary | 1.14 MB | 0.416 | 14.326 | 23.073 | 30.865 | 0.018 |
| binary + int8 rescore | 10.30 MB combined | 0.858 | 11.427 | 13.688 | 20.479 | 0.249 |

Memory values are vector-storage estimates, not total process or serving memory. Binary-plus-int8 rescoring retains both representations; its combined storage is approximately 10.30 MB.

### Interpretation and supported workload

- Int8 retains 98.2% recall@10 while reducing vector storage by approximately 75% relative to float32.
- Binary-only storage is smallest, but recall falls to 41.6%; it is not suitable as a standalone replacement at this recall level.
- Binary candidate generation followed by int8 rescoring recovers recall to 85.8%, using approximately 10.30 MB for both vector representations.
- On this machine and workload, int8 was slower than float32 exact search. Quantization reduced storage but did not improve measured latency.
- Float32 exact search remains the accuracy baseline.

This benchmark supports a measured 25,000-vector retrieval workload with 50 temporal holdout queries. It does not establish a 100,000- or million-vector serving capacity, production throughput, or tail-latency guarantees.

### Method and limitations

The database consists of the first 25,000 training vectors. Queries are selected from the artifact's later-period test partition beginning at the fixed temporal cutoff. The comparison uses exact float32 top-k results as the recall reference. The optional FAISS HNSW branch was disabled to limit memory use.

Latency percentiles are based on only 50 queries and are sensitive to local machine load, memory pressure and runtime variability. In particular, p99 is not a stable production SLO estimate. Storage figures cover vector representations only; they exclude metadata, process overhead and other indexes.

Raw machine-readable output: `results/quantization_temporal.json`.
Artifact: `artifacts/complaintiq_full_minilm`.
