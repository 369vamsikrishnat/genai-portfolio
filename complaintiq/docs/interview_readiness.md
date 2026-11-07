# ComplaintIQ ? Interview readiness

## 60-second explanation

ComplaintIQ is a local-first prototype for bank and fintech complaint operations. It classifies complaint narratives, applies deterministic risk rules, retrieves similar historical complaints, and prepares evidence-referenced response templates. Decisions enter a human review queue, and approval is required before a send record can be created. It uses CFPB public complaint data and includes a FastAPI service, Streamlit UI, Docker Compose setup, evaluation reports and Locust load tests. It is a research/demo project, not a production or compliance-certified service.

## Architecture

1. Ingest CFPB data, normalize to Parquet, apply regex-based PII masking and template deduplication.
2. Build artifacts using chronological training and later-period holdout partitions.
3. Validate and sanitize API input; classify product; optionally escalate configured low-confidence cases to an LLM.
4. Apply deterministic risk flags and routing.
5. Retrieve historical precedents using BM25 and dense retrieval.
6. Generate deterministic evidence templates with citations; refuse insufficient evidence.
7. Record review decisions and approval-gated send transitions.
8. Serve through FastAPI and Streamlit in Docker Compose.

## Numbers to know

| Experiment | Result | Limitation |
|---|---|---|
| MiniLM classifier | Macro-F1 0.6321; 329,940 records | Separate artifact; 100k train, 229,940 later holdout |
| Hashing classifier | Macro-F1 0.4564 | Different 67,452-record evaluation |
| Retrieval | BM25 Hit@5 0.697; dense 0.510; RRF 0.667 | Product+issue proxy labels, not human relevance |
| Spike scan | 139 alerts across 124 weeks | No incident labels |
| Draft evaluation | 49/50 successful | Structural checks, not legal or quality validation |
| Quantization | Int8 Recall@10 0.982; 9.16 MB vs 36.62 MB | 25k vectors, 50 queries; slower than float32 |
| Load test | 20 users, 668 requests, zero failures, 24.37 req/s | 30 seconds; local mock/hash/lexical stack |

## Likely interview questions

**Why CFPB data?** It provides public complaint narratives and taxonomy labels. Consumer submissions are not independently verified findings and are not a random sample of all banking complaints.

**How did you avoid temporal leakage?** Records are ordered chronologically. The MiniLM artifact trains through 2025-09-23 and holds out records beginning 2025-09-24. The older hashing evaluation has a separate split.

**Why a classifier/LLM cascade?** The classifier handles confident cases; configured low-confidence cases can be escalated. Cost figures are estimates based on assumed token prices, not observed provider bills.

**What does Macro-F1 0.6321 mean?** Product classification on the separate MiniLM artifact's temporal holdout. It does not measure fraud detection, draft quality or business outcomes.

**How are fraud cases handled?** Rules detect risk language such as identity theft/fraud and route flagged cases to human review. A flag is not a verified fraud determination.

**Are drafts LLM-generated?** No. The current draft path is a deterministic evidence template with retrieved complaint references. It refuses insufficient evidence.

**What do retrieval metrics prove?** Hit@5 uses product-and-issue agreement as proxy relevance. It does not establish human-perceived usefulness.

**What did the load test prove?** The local demo handled the measured 30-second mixed workload with zero request failures at up to 20 users. It does not establish production capacity or cloud performance.

**Why was int8 slower?** The result reflects this implementation, index size and machine. Quantization reduced storage but did not improve measured latency.

**What is needed before production?** Pin dependencies and artifact versions; rebuild under the serving scikit-learn version; secure UI and metrics; add TLS, secret rotation, backups, distributed rate limiting, monitoring, threat modeling and privacy/legal review. Add human-labeled evaluation and sustained realistic load tests.

## Limitations to volunteer

- scikit-learn artifact 1.9.1 versus runtime 1.9.0 compatibility warning.
- Starlette/httpx TestClient deprecation warning.
- Unauthenticated UI and public metrics; health endpoint is liveness-only.
- Regex masking is not guaranteed anonymization.
- No human-labeled risk or incident ground truth.
- No production deployment, regulatory certification or legal adequacy claim.

## Demo checklist

- Show ordinary triage and an identity-theft/fraud case routed to review.
- Show a draft and explain that citations are historical context, not proof.
- Demonstrate review and approval/rejection audit flow.
- Explain why the two classifier scores belong to separate experiments.
- Show load-test and quantization results with their limitations.
