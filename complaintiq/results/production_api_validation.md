# Production API, audit, and observability validation

**Validation type:** local FastAPI `TestClient` integration against the existing real CFPB artifact bundle. This is not a production security, load, or regulatory-compliance certification.

## Artifact and end-to-end workflow

Loaded `artifacts/complaintiq` without retraining: a deterministic 100,000-row sample deduplicated to 67,452 records, with 53,961 training rows, hashing embeddings (384 dimensions), built at `2026-10-30T15:30:51`. This is a real-CFPB trained artifact, not the complete CFPB source. Safe test requests exercised classification, risk flags, retrieval, evidence-grounded drafting, review, and send approval:

- Triage returned a product label and confidence; an unauthorized-transfer input triggered `identity_theft_fraud`.
- A related request returned citations matching its retrieved precedent IDs. Retrieved complaint narrative snippets were excluded from draft and queue responses.
- A prompt-injection test was flagged for review.
- An unrelated balcony-gardening query was refused. Its maximum dense similarity was 0.2182, but lexical rerank was 0.0882, below the new minimum of 0.1. On a separate sample of 150 strictly later, template-deduplicated CFPB queries searched against a training-only index, the minimum lexical rerank was 0.1198; none fell below 0.1. This is a threshold sanity check, not human relevance evaluation.
- Sending a draft before approval was denied; an approved draft was sent; a rejected draft remained unsendable.

## Endpoint coverage

| Endpoint | Validation |
|---|---|
| `GET /health` | 200 with and without artifacts; liveness only |
| `POST /triage` | Real-artifact success; prompt-injection review; invalid input 422; missing key 401; missing artifacts 503; simulated inference failure 500 |
| `POST /draft` | Cited draft; insufficient-evidence refusal; blank input 422 |
| `GET /queue` | Pending review; retrieved narrative snippets omitted |
| `POST /queue/{id}/approve` | Approval recorded |
| `POST /queue/{id}/reject` | Rejection recorded |
| `POST /decisions/{id}/send` | 200 after approval; 403 after rejection |
| `GET /metrics` | 200 with and without artifacts |

Validation errors no longer echo submitted text. Server errors return a generic response with the request ID.

## Audit and observability

Audit records capture request IDs, UTC timestamps, model and artifact identifiers, prompt version, hashed input, decision/status, and cited complaint IDs. Approval, rejection, send, and failure actions are recorded as events. Simulated inference failures record the exception type but not the exception message or complaint text. A migration test confirms compatibility with the earlier SQLite schema.

Structured access logs include request ID, method, route template, status, duration, and error type when applicable; request bodies are not logged. `/metrics` exposes HTTP request/status/latency metrics and triage/draft/error counters, including when model artifacts are unavailable.

## Changes and limitations

- Added request-ID propagation, non-echoing validation errors, safe generic server-error responses, API request metrics, and artifact-independent metrics availability.
- Added audit schema migration and event records for decisions, review actions, sends, and inference errors.
- Removed retrieved narrative snippets from draft and review-queue API/audit payloads.
- Added a lexical evidence floor to avoid drafting on weak-overlap results. It preserves all 150 sampled later real queries in the small threshold check; this does not establish retrieval precision.
- New artifact builds record artifact/runtime versions. The current saved manifest does not; the audit version falls back to its build timestamp.

The current environment emitted scikit-learn unpickle warnings (artifact objects report 1.9.1; runtime is 1.9.0) and a Starlette/httpx TestClient deprecation warning. Although endpoint tests completed, align and pin these dependencies before deployment. `/metrics` is public and `/health` is liveness-only. No load/concurrency, transport security, operational secret-management, security certification, or regulatory-compliance validation was performed.

## Tests

Focused API, audit, service, and draft-evaluation tests passed: **19 passed** after the model/artifact-version changes. After switching structured logs to explicit UTC timestamps, the real-artifact API workflow test passed again (**1 passed**); the API/audit subset also passed after the model-version assertion (**13 passed**). Ruff and `git diff --check` passed.
