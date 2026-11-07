# ComplaintIQ ? Resume bullets

**ComplaintIQ | Python, FastAPI, Streamlit, scikit-learn, Sentence Transformers, DuckDB, Docker, Locust**

- Built a local-first complaint triage and evidence workflow over 329,940 template-deduplicated CFPB records; a separate MiniLM temporal evaluation reported product-classification Macro-F1 of 0.6321.
- Implemented FastAPI and Streamlit workflows for classification, rule-based fraud-risk flags, precedent retrieval, evidence-template drafting, human review queues, approval-gated send records, and audit logging.
- Evaluated vector quantization on 25,000 vectors and 50 later-period queries: int8 retained 98.2% Recall@10 against exact float32 while reducing vector storage by approximately 75%, though search was slower.
- Load-tested the local Docker Compose demo: 668 requests, zero failures, 24.37 requests/second at 20 concurrent users over 30 seconds; aggregate p50/p95 was 380/1,100 ms.

## Important metric boundaries

- The 0.6321 score belongs to the 329,940-record MiniLM artifact (100k train, 229,940 later holdout). The separate 67,452-record hashing evaluation reported Macro-F1 0.4564. Do not combine these results.
- Load testing used mock LLM, hashing embeddings and lexical reranking. It is not a Gemini + MiniLM or production capacity benchmark.
- Quantization Recall@10 measures overlap with exact float32 neighbors, not human relevance; only 50 queries were used.
- The 139 spike alerts have no independently labeled incidents. False-alert rate and predictive accuracy are unknown.
- Drafts are deterministic evidence templates, not LLM-generated personalized responses or legal advice.
- Do not claim production deployment, regulatory certification, verified fraud detection or guaranteed anonymization.

## Metric evidence

| Claim | Source |
|---|---|
| MiniLM score and corpus | artifacts/complaintiq_full_minilm/manifest.json |
| Hashing classifier | results/classifier_metrics.md |
| Quantization | docs/scale.md |
| Load test | docs/load_test.md |
| Spike evaluation | docs/spikes.md |
| Drafting and guardrails | docs/draft_evaluation.md; docs/guardrail_checks.md |
| API validation | results/production_api_validation.md |
| Deployment limitations | docs/DEPLOYMENT.md |
