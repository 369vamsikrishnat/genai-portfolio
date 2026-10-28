# ComplaintIQ

Complaint triage, emerging-issue detection and **cited** response drafting over the public
[CFPB Consumer Complaint Database](https://www.consumerfinance.gov/data-research/consumer-complaints/).

**Buyers it is designed for:** head of complaints handling, compliance officer, customer-ops lead.
**What they get:** fewer misrouted complaints, early warning when an issue spikes, consistent drafts that
cite precedent, and an audit trail explaining every decision.

> **Read this first: status of this codebase**
> * **Verified (automated tests pass):** PII redaction, BM25/dense/RRF/rerank retrieval, ablation harness,
>   quantisation (int8/binary) + scale harness, classifier/LLM cascade + cost accounting, spike detector,
>   drafter guardrails, audit log + approval gate, rate limiter/metrics, service end-to-end on **synthetic** data.
> * **Written but NOT executed by the author** (no network/packages in the authoring sandbox): the DuckDB
>   ingest (`ingest.py`, test auto-skips without duckdb), the FastAPI app, the Streamlit UI, Docker/compose,
>   the Ollama and Gemini clients, the `sentence-transformers` embedder / cross-encoder reranker, the optional
>   FAISS HNSW row, and CI lint (`ruff`). **Expect to fix small issues there on first run**; the logic they wrap is tested.
> * **No result in this repo is real until you produce it.** Everything under `docs/` and `results/` that comes
>   from `synth` data / the `hashing` embedder / the `mock` LLM is stamped with a WARNING. Never put those numbers
>   on a resume.

## Quickstart (2 minutes, synthetic data, no downloads)

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev,data]"
pytest -q                          # unit + end-to-end tests
python -m complaintiq demo         # synth data -> index -> triage + cited draft
python -m complaintiq eval-retrieval && python -m complaintiq eval-cascade && python -m complaintiq spikes --brief
```

## Real-data path (this is what produces resume-worthy numbers)

**0. Install everything**
```bash
pip install -e ".[dev,data,embed,serve,faiss]"
```
**1. Ingest** (streams the CFPB zip; partitions Parquet by year/month; redacts PII; dedupes; idempotent)
```bash
python -m complaintiq download            # https://files.consumerfinance.gov/ccdb/complaints.csv.zip (large)
python -m complaintiq ingest --since 2020 # re-running on the same file is a no-op (SHA-256 checkpoint)
```
Why `--since 2020`: CFPB renamed several products/issues over time; mixing eras makes label noise.
Open a notebook and **count rows with narratives before planning scale**: only a subset of complaints have one.

**2. Local LLM (free)** - install [Ollama](https://ollama.com), then `ollama pull qwen2.5:7b`.
```bash
export CIQ_LLM=ollama CIQ_OLLAMA_MODEL=qwen2.5:7b
```
Gemini free tier works too (`CIQ_LLM=gemini`, `GEMINI_API_KEY=...`) but its limits are tight and change often;
use it for small samples, not bulk runs. Free-tier inputs may be used by Google to improve models; this project
only sends public CFPB text.

**3. Build a 100k index with real models, then run every evaluation**
```bash
export CIQ_EMBEDDER=bge-small CIQ_RERANKER=cross-encoder
python -m complaintiq build --src data/parquet --sample 100000 --since 2020
python -m complaintiq eval-retrieval --n-queries 500   # -> docs/ablation.md
python -m complaintiq eval-cascade --n 500             # -> docs/cost_table.md  (needs CIQ_LLM=ollama)
python -m complaintiq spikes --brief                   # -> results/spikes.json
python -m complaintiq scale --sizes 100000 1000000     # -> docs/scale.md (needs >=1M embedded narratives)
```
Embedding 100k+ narratives on CPU is slow: embed on a free Kaggle/Colab GPU and copy `vectors.npy` back, or start
with `--sample 20000`. For 1M, build on Kaggle/Colab.

**4. Hand-label risk flags (the part that makes your evals defensible)**
```bash
python -m complaintiq label-sample --src data/parquet --since 2020 --n 250 --out evals_labels.csv
# open the CSV, fill risk_flag with 0/1 (and severity) BY HAND, then:
python -m complaintiq eval-risk --sheet evals_labels.csv
```
**5. Serve**
```bash
python -m complaintiq serve        # API on :8000   (docs at /docs, Prometheus metrics at /metrics)
streamlit run src/complaintiq/ui/streamlit_app.py
docker compose up --build          # api :8000 and ui :7860 (demo mode unless you mount real artifacts)
locust -f loadtest/locustfile.py --host http://localhost:8000   # set CIQ_RATE_LIMIT=100000 first
```

## Design decisions worth being able to explain
* **Cascade triage.** A logistic-regression classifier on embeddings handles confident cases; only
  `confidence < CIQ_LLM_THRESHOLD` goes to the LLM. `eval-cascade` runs the LLM once per sample row and *simulates*
  every threshold, so one pass yields the whole cost-vs-F1 curve. **Cost is estimated** (token counts x list price,
  overridable via env); free tiers make real spend $0. Say "estimated" on the resume.
* **Temporal split.** Test = the latest 20% by date, so near-duplicate template complaints don't leak.
* **Retrieval eval uses weak labels** (same product+issue = relevant) and reports Precision@k, not Recall@k (with
  large relevant sets recall is meaningless). Validate the proxy by hand-checking ~100 queries and disclose it.
* **The drafter does not reproduce past response letters** because CFPB publishes only the response *category*.
  It cites similar resolved complaints and their outcomes. Refusal fallback `NOT_ENOUGH_PRECEDENT` fires when the
  best dense similarity is below `CIQ_MIN_DENSE_SCORE` (tune it on real data).
* **Guardrails.** Injection screen before any LLM call (suspected injection never reaches the model; it goes to a
  human), citation validator (every `[CFPB-id]` must be a retrieved precedent), and **no draft can be marked sent
  without a human approval record** (`AuditLog.mark_sent` raises `NotApproved`; tested).
* **Spike detector.** Weekly counts per (company, issue); flags on count, z-score and a Gamma-Poisson predictive
  tail probability with Bonferroni correction. History: a plug-in Poisson p-value gave ~4 false alarms in 12
  noise-only scans because the baseline rate is itself estimated; the fix is covered by a regression test
  (<=3 false alarms in 20 noise-only scans). Real data is overdispersed and seasonal: **backtest on known events**
  and report precision on spikes you verify.
* **Quantisation.** int8 saves 4x memory and (in numpy) is *slower* than float32; binary saves 32x but needs
  rescoring for usable recall. `scale` reports recall vs exact, memory, build time and p50/p95/p99 so you can state
  the trade-off from your own numbers.
* **PII.** CFPB masks many identifiers already; regexes here are defence in depth, not a guarantee.

## Differences from the original plan
No pgvector (numpy exact search + optional FAISS HNSW instead, simpler to run free); Streamlit instead of React;
the monetary-relief priority model is cut; spike clustering uses sklearn HDBSCAN on an SVD projection (no UMAP);
the full 3.8M-narrative rung is optional.

## Resume checklist (fill ONLY from your own `results/*.json`)
* Add the project after `eval-cascade` produces real numbers. Label it a personal project on public data.
* Every number must trace to a file in `results/`. Be ready to say how each was measured.
* Don't say "production deployment"; say "containerised service with CI, structured logs, metrics and load tests".
* Template (replace brackets): *Built ComplaintIQ, a complaint triage and cited-drafting system over [N] CFPB
  narratives: hybrid retrieval ablation ([best config] Hit@1 [x] vs BM25 [y]); classifier-first cascade reaching
  [F1] macro-F1 at [esc]% LLM escalation (estimated $[c]/1k vs $[l]/1k LLM-only); weekly spike detector backtested
  on [k] events; human-approval gate with zero unapproved sends in tests; p95 [ms] at [u] concurrent users.*

## Layout
```
src/complaintiq/  ingest  data  synth  pii  embed  retrieve  quant  metrics  classify  llm  risk
                  spikes  draft  audit  service  pipeline  observability  cli  api/app.py  ui/streamlit_app.py
                  evals/{retrieval,scale,risk}.py
tests/            unit + end-to-end (synthetic) + ingest roundtrip (needs duckdb)
loadtest/         locust scenario        scripts/entrypoint.sh   Dockerfile  docker-compose.yml
docs/             generated: ablation.md  cost_table.md  scale.md
```
Data: CFPB complaint data is public; see the CFPB's terms and disclaimers (it is not a statistical sample).
