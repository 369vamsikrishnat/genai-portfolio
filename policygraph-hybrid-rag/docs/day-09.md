# Day 9 — Production Plumbing + Week 2 Consolidation

## Goal

Add production-oriented plumbing around the existing PolicyGraph Hybrid RAG pipeline:

* API-key authentication
* Rate limiting
* Query cost tracking
* Background ingestion jobs
* Health and metrics endpoints
* Streamlit demo UI
* Dockerized API, UI, and PostgreSQL
* Langfuse tracing

---

## 1. FastAPI API

Created:

```text
src/api/main.py
```

The FastAPI application exposes:

* `POST /query`
* `POST /ingest`
* `GET /job/{id}`
* `GET /health`
* `GET /metrics`

### API-key authentication

Protected endpoints require:

```text
X-API-Key
```

The API key is configured through the `API_KEY` environment variable.

The API key used by FastAPI is separate from the `GEMINI_API_KEY`, which is used internally for Gemini requests.

Invalid or missing API keys return:

```text
401 Unauthorized
```

---

## 2. Rate Limiting

Added `slowapi` rate limiting.

Protected endpoints use:

```text
30 requests/minute
```

The rate limiter uses the client's remote address as the rate-limit key.

### Test

Sent 31 rapid requests to the protected endpoint.

Result:

```text
429 Too Many Requests
```

This confirmed that rate limiting is working.

---

## 3. Background Ingestion

Added:

```text
POST /ingest
```

The endpoint creates a job ID and runs document loading/chunking as a FastAPI background task.

Example flow:

```text
POST /ingest
      ↓
job_id returned
      ↓
background ingestion
      ↓
GET /job/{job_id}
      ↓
completed / failed
```

The ingestion job currently loads the document and performs section-aware chunking.

A test using:

```text
data/synthetic_policies/policy_1.txt
```

completed successfully and produced:

```text
12 chunks
```

---

## 4. Cost Tracking

Created:

```text
src/api/cost_tracker.py
```

`CostTracker` records:

* total queries
* total input tokens
* total output tokens
* total cost
* average cost per query

Gemini pricing configured for the tracker:

```text
Input:  $0.75 / 1M tokens
Output: $3.75 / 1M tokens
```

Thinking tokens are included with output tokens for the cost calculation.

Example observed metrics:

```json
{
  "total_queries": 1,
  "total_input_tokens": 626,
  "total_output_tokens": 686,
  "total_cost": 0.003042,
  "average_cost_per_query": 0.003042
}
```

The cost is an application-level estimate based on token usage and configured pricing. It is not an invoice from Gemini.

The tracker currently stores its state in memory, so metrics reset when the API process restarts.

---

## 5. Metrics Endpoint

Added:

```text
GET /metrics
```

It returns:

```text
total_queries
total_input_tokens
total_output_tokens
total_cost
average_cost_per_query
```

The endpoint is protected by the API key.

---

## 6. Streamlit Demo UI

Created:

```text
src/ui/app.py
```

The UI allows a user to:

1. Enter a policy question.
2. Send the question to the FastAPI `/query` endpoint.
3. Display the generated answer.
4. Display query cost.
5. Display a confidence bar.
6. Expand retrieved citations and view their scores.

The UI communicates with the API rather than directly running the RAG pipeline.

Architecture:

```text
Streamlit UI
     ↓
FastAPI
     ↓
RAG Pipeline
     ↓
Dense + BM25
     ↓
RRF
     ↓
Cross-Encoder Reranking
     ↓
Gemini Generation
```

---

## 7. Dockerization

Added:

```text
Dockerfile
```

Updated:

```text
docker-compose.yml
```

The Docker Compose setup runs:

```text
PostgreSQL + pgvector
FastAPI API
Streamlit UI
```

The API connects to the Docker PostgreSQL service through:

```text
DATABASE_URL
```

The database uses the existing `document_chunks` schema and pgvector extension.

Because the Docker PostgreSQL instance is separate from the previous local PostgreSQL instance, the schema had to be initialized using:

```text
infra/schema.sql
```

The policy data was then loaded into the Docker database using the existing dense retrieval module.

---

## 8. Docker End-to-End Test

Docker Compose successfully started:

```text
policygraph-postgres
policygraph-api
policygraph-ui
```

The PostgreSQL container became healthy.

After initializing the database and loading the policy chunks, the Streamlit UI successfully queried the Dockerized API.

Test question:

```text
What is the coverage for flood damage?
```

The system returned a grounded answer referring to the flood-damage coverage clause.

This verified the complete Dockerized query path:

```text
Browser
  ↓
Streamlit
  ↓
FastAPI
  ↓
PostgreSQL / pgvector
  ↓
Hybrid retrieval
  ↓
Reranking
  ↓
Gemini
  ↓
Answer
```

---

## 9. Langfuse Tracing

Added Langfuse tracing to the RAG pipeline using the current Langfuse SDK.

The pipeline is wrapped with:

```python
@observe(name="policygraph-rag-pipeline")
```

A test query successfully produced a trace in Langfuse Cloud.

Langfuse is configured as an external cloud service rather than running a local Langfuse container.

---

## 10. Environment Variables

The production-style configuration uses environment variables for secrets and service configuration.

Important variables include:

```text
API_KEY
GEMINI_API_KEY
LANGFUSE_PUBLIC_KEY
LANGFUSE_SECRET_KEY
LANGFUSE_BASE_URL
DATABASE_URL
API_URL
```

`.env` is excluded from Git through `.gitignore`.

Secrets are therefore not included in the staged Day 9 changes.

---

## 11. Day 9 Verification

### API

* [x] FastAPI application created
* [x] API-key authentication works
* [x] `/query` works
* [x] `/ingest` creates background jobs
* [x] `/job/{id}` reports job status
* [x] `/health` works
* [x] `/metrics` works

### Rate limiting

* [x] `30/minute` limit configured
* [x] 429 response verified

### Cost tracking

* [x] Token usage captured
* [x] Query cost calculated
* [x] Average cost per query calculated

### UI

* [x] Streamlit UI created
* [x] Query submission works
* [x] Answer displayed
* [x] Citations displayed
* [x] Confidence displayed
* [x] Query cost displayed

### Docker

* [x] Dockerfile created
* [x] Docker Compose configured
* [x] PostgreSQL + pgvector running
* [x] FastAPI running
* [x] Streamlit running
* [x] Docker database initialized
* [x] End-to-end Docker query verified

### Observability

* [x] Langfuse tracing added
* [x] Pipeline trace verified in Langfuse

---

## Key Takeaways

### API key vs Gemini API key

The application's API key and Gemini API key have different purposes.

```text
Client
  ↓ X-API-Key
FastAPI
  ↓ GEMINI_API_KEY
Gemini
```

`API_KEY` protects the application's API.

`GEMINI_API_KEY` authenticates requests from the application to Gemini.

### Cost tracking

The application can calculate an estimated cost from token usage:

```text
input tokens × input price
+
output/thinking tokens × output price
```

This gives application-level cost visibility per query.

### Background jobs

Longer ingestion work does not have to block the initial API response.

```text
Request → job_id
           ↓
       background task
           ↓
        job status
```

### Docker networking

Inside Docker Compose, services communicate using service names rather than `localhost`.

For example:

```text
postgres:5432
api:8000
```

This is different from accessing services from the host machine.

### Observability

Langfuse provides visibility into the RAG pipeline execution, making it possible to inspect pipeline traces rather than treating the RAG system as a black box.
