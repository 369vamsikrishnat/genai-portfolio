# ComplaintIQ

ComplaintIQ is a local-first prototype for classifying consumer complaints, identifying rule-based risk
flags, retrieving similar complaints, drafting evidence-referenced responses, and recording human review
decisions. Its public dataset source is the [CFPB Consumer Complaint Database](https://www.consumerfinance.gov/data-research/consumer-complaints/).

**This is a research/demo project, not a production or compliance-certified service.** The default
components use hashing embeddings and a mock LLM. They are useful for offline development, not as evidence
of semantic retrieval or language-model quality.

## Quickstart

Requires Python 3.10+ (Python 3.12 is the tested local runtime).

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev,data,serve]"
pytest -q
ruff check .
python -m complaintiq demo
```

For macOS/Linux, create/activate it with `python3 -m venv .venv` and
`source .venv/bin/activate`. The demo uses generated synthetic records and writes its artifacts under
`artifacts/demo` when no demo bundle is already present; it does not download real complaints.

## Run locally

```powershell
python -m complaintiq serve --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/docs` for the interactive API docs. See [Deployment, configuration, API,
architecture and evaluation details](docs/DEPLOYMENT.md) before using real data or exposing a service.

## Docker demo

With Docker Desktop running:

```powershell
docker compose up --build
```

The API is at `http://localhost:8000`; the Streamlit demo is at `http://localhost:7860`. Docker Compose
uses a named artifact volume and builds a synthetic demo artifact on its first start if that volume is
empty. The API key is unset by default, metrics are public, and the health endpoint is liveness-only.
This configuration is for local demonstration, not Internet-facing deployment. To use trained artifacts,
follow the real-artifact Docker instructions in [DEPLOYMENT.md](docs/DEPLOYMENT.md).

## Evaluation snapshot

Reports are stored under [`results/`](results/). The current local report set uses a
deterministic 100,000-row sample from the real CFPB processed source; template deduplication left 67,452
records (53,961 train, 13,491 later test). It is **not** the complete CFPB dataset.

| Area | Observed result | What it supports |
|---|---|---|
| Classifier | Temporal test Macro-F1 0.4564; Weighted-F1 0.6462; accuracy 0.6161; ECE 0.055 | Held-out product-label classification on this sampled dataset |
| Retrieval | Proxy-label Hit@5: BM25 0.697, dense 0.510, RRF 0.667 | Same-product-and-issue proxy only; not human relevance judgments |
| Risk rules | 5,576/13,491 temporal holdout rows flagged (41.3%) | Coverage only; there are no hand-labeled risk outcomes |
| Spike detection | 139 alerts in a chronological scan of 2,004,605 source rows | Descriptive alerts only; no labeled incidents or measurable false-alert rate |
| Drafting | 100 later queries; 99 successful drafts, citation/template checks passed, 1 refusal | Automated structural checks; no human-judged helpfulness or legal suitability |
| Performance | Local 1k/2.5k/5k workloads; 5k-index RRF-rerank p50/p95/p99 24.595/96.777/110.965 ms | Small, hardware-specific TestClient and benchmark measurements; not capacity claims |

Classifier and evaluation results are from saved reports; rerun commands before relying on them. Retrieval
figures are taxonomy-proxy metrics, spike counts are not true positives, and performance numbers are not
production SLAs. The measured external model spend in the benchmark was $0 because it used MockLLM. Its
separate $0.1605/1,000 escalated-triage estimate is a configurable token-price scenario, not an observed bill.
See [the full report/limitations index](docs/DEPLOYMENT.md#evaluation-results-and-interpretation).

## Additional measured experiments

These are separate experiments and must not be combined with the 67,452-row report set above.

### Real CFPB MiniLM artifact

A separate artifact, `artifacts/complaintiq_full_minilm`, contains 329,940 template-deduplicated real CFPB records, with 100,000 training rows and 229,940 later-period holdout rows. Its saved manifest reports classifier Macro-F1 **0.6321**. This is a different artifact and evaluation from the hashing-based 67,452-row report set above; the scores are not directly interchangeable.

### Vector quantization

A temporal retrieval experiment used 25,000 training vectors and 50 later-period holdout queries from the MiniLM artifact. Recall@10 is overlap against exact float32 neighbors, not human relevance.

| Representation | Vector storage | Recall@10 | p50 (ms) | p95 (ms) | p99 (ms) |
|---|---:|---:|---:|---:|---:|
| float32 exact | 36.62 MB | 1.000 | 6.125 | 89.278 | 605.797 |
| int8 | 9.16 MB | 0.982 | 79.384 | 146.914 | 176.985 |
| binary | 1.14 MB | 0.416 | 14.326 | 23.073 | 30.865 |
| binary + int8 rescore | 10.30 MB | 0.858 | 11.427 | 13.688 | 20.479 |

Int8 reduced vector storage by approximately 75% while retaining 98.2% recall@10, but was slower than float32 in this workload. Binary-only recall was 41.6%. The 50-query sample makes tail percentiles unstable; storage excludes metadata and process overhead. This does not establish million-vector capacity or production latency. See [the quantization methodology and limitations](docs/scale.md).

### Docker API load test

The local Docker Compose demo stack was tested with Locust for 30 seconds per run, using mock LLM, hashing embeddings, and lexical reranking.

| Concurrent users | Requests | Failures | Throughput (req/s) | Average (ms) | p50 (ms) | p95 (ms) |
|---:|---:|---:|---:|---:|---:|---:|
| 5 | 269 | 0 | 9.73 | 172.45 | 87 | 610 |
| 10 | 265 | 0 | 10.23 | 580.70 | 320 | 2,100 |
| 20 | 668 | 0 | 24.37 | 441.60 | 380 | 1,100 |

All three short runs recorded zero request failures. At 20 users, endpoint p95 was 980 ms for triage, 1,400 ms for draft, and 46 ms for health. These are local demo measurements, not Gemini + MiniLM performance, production capacity, or an SLA. See [the load-test report](docs/load_test.md).

## Portfolio preparation

- [Resume bullets](docs/resume_bullets.md)
- [Interview-readiness guide](docs/interview_readiness.md)

## Project structure

```text
src/complaintiq/       package, CLI, FastAPI service, Streamlit UI
src/complaintiq/evals/ evaluation and benchmark code
tests/                 unit, CLI, integration and real-artifact tests
docs/                  deployment guide and generated evaluation markdown
results/               evaluation JSON/Markdown reports (may be regenerated)
data/                  local CFPB input/processed files; ignored by Git
artifacts/              local trained/demo artifacts; ignored by Git
Dockerfile              API/UI image
docker-compose.yml      local API and UI services
```

Local raw data, trained artifacts, environment files, and SQLite audit databases are excluded from Git.
Do not add raw complaint text, credentials, or large dataset archives to the repository.
