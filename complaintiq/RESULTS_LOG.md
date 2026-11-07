# ComplaintIQ Results Log



## Phase 0 — Freeze the basics



### Completed checks



- Date: 2026-11-04

- Test command: `pytest -q`

- Result: 66 passed, 1 Starlette deprecation warning.

- Runtime: 134.76 seconds.

- scikit-learn: pinned to 1.9.1.

- Pipeline syntax: `python -m py_compile .\src\complaintiq\pipeline.py` — passed with no output.

- Pipeline updated to support a fixed test cutoff and classifier-only builds.

- Manifest corrected to record the post-deduplication row count separately.



### Pending



- Choose and freeze the test cutoff date.

- Save frozen test complaint IDs and SHA-256.

- Complete the 100-narrative manual privacy review.

- Review stale synthetic artifacts and local paths.

- Commit Phase 0 after all checklist items pass.



### Frozen test set — verified



- Cutoff: 2025-09-24

- Source: `data/processed`

- Rows after template de-duplication: 1,056,264

- Frozen test complaint IDs: 229,940

- Test date range: 2025-09-24 to 2026-08-11

- ID file: `artifacts/frozen_test_2025-09-24/test_ids.txt`

- SHA-256: `7239f325421c0eba7221e739740707ad0425bf50052179350c21816e3ff13f08`

- Verification: Python SHA-256 independently matched PowerShell `Get-FileHash`.



### Manual privacy review — completed



- Sample size: 100 randomly selected, template-de-duplicated narratives.

- Random seed: 42.

- Source file: `results/privacy_review_100.csv`

- Clearly visible, unmasked personal identifiers: 0 of 100.

- Phone, email, SSN and card-number checks: no matches.

- Generic account or transaction descriptions were not counted as exposed account details.

- Finding: identifiers in the reviewed narratives appeared masked.

- Limitation: this is a 100-record spot-check, not proof of zero PII across the full dataset.



### Synthetic artifact cleanup — completed



- Removed `results/cascade.json` — confirmed `llm: mock` and `simulated: true`.

- Removed `docs/cost_table.md` — explicitly marked simulated and WARNING.

- Preserved `src/complaintiq/cli.py` and its evaluation generator.

- No real-LLM results were deleted.

- Hard-coded local-path scan: no matching references found.



### Dependency pin — verified



- `pyproject.toml` now specifies `scikit-learn==1.9.1`.

- Installed version verified: `1.9.1`.

- Project requirement and active environment match.



## Phase 1 — Data quality and privacy review (2026-11-04)



- Deterministic sample: 200,000 rows; duplicate complaint IDs: 0.

- Template repetition: 34.8%; 130,429 distinct narratives in the sample.

- Post-redaction PII pattern checks: 0 matches across SSN, card, email, phone and number patterns.

- Manual privacy review: 100 template-deduplicated narratives (seed 42); 0 clearly visible unmasked identifiers. This is a spot-check, not proof of zero PII across the full dataset.

- Ingestion join: 2,004,605 joined rows; 31 unmatched archive IDs; narrative coverage of main dataset: 14.06%.

- Distinct narrative hashes in joined data: 1,056,264.

- Report: `docs/data_quality.md`; manual review: `results/privacy_review_100.csv`.



## Phase 2 — Frozen hashing classifier (2026-11-04)



- Build: `python -m complaintiq build --src data/processed --out artifacts/complaintiq_frozen --since 2024 --sample 100000 --embedder hashing --test-cutoff 2025-09-24 --classifier-only`

- Evaluation: `$env:CIQ_ARTIFACTS_DIR="artifacts/complaintiq_frozen"; python -m complaintiq eval-classifier`

- Frozen test IDs: 229,940; exact match with Phase 0 frozen set.

- Training rows: 100,000

- Macro-F1: 0.4909

- Weighted-F1: 0.6449

- Accuracy: 0.6182

- Expected calibration error: 0.0105

- Output: `results/classifier_metrics.json`, `results/classifier_metrics.md`



### Full-training hashing benchmark — 2026-11-04



- Artifact: `artifacts/complaintiq_full_hashing`

- Training rows: 826,324

- Frozen test rows: 229,940 (IDs match Phase 0)

- Macro-F1: 0.5131

- Weighted-F1: 0.6602

- Accuracy: 0.6355

- Majority baseline: 0.2870

- Expected calibration error: 0.0432

- Embed time: 265.65 seconds

- Evaluation: `python -m complaintiq eval-classifier`

- Outputs: `results/classifier_metrics.json`, `results/classifier_metrics.md`



## Phase 5 — Risk definition freeze (2026-11-04)



- Definition: `RISK_DEFINITION.md`

- Six explicit risk triggers and negative-label rules documented.

- Ten consistency anchors documented; all outside the original 250-row labelled dataset.

- Legal escalation clarified: stated or conditional intent counts; merely noting that legal action may be possible does not.

- Anchor 10336024 confirmed positive (1); replacement legal-language-only negative anchor: 10380544 (0).

- Labels and risk rules unchanged.

- Evaluation limitation documented: monitor development-set positive rate; review if above approximately 30%.



### Task 2.3 — Current risk-rule baseline (2026-11-05)



- Command: `python -c "import json; from pathlib import Path; from complaintiq.evals.risk import score_rules; p=Path('results/risk_dev_eval_v0.json'); p.write_text(json.dumps(score_rules('results/risk_dev_labels_300_v1.csv'), indent=2)+'\n', encoding='utf-8')"`

- Frozen development labels: 300 rows; 55 positives.

- Precision: 0.848; recall: 0.509; F1: 0.636; accuracy: 0.893.

- Confusion counts: TP 28; FP 5; FN 27.

- Output: `results/risk_dev_eval_v0.json`

- Verification: saved JSON metrics independently read back and matched.



### Task 2.4 — Risk rule error analysis (2026-11-05)



- Dataset: `results/risk_dev_labels_300_v1.csv` (300 frozen labels).

- Baseline: precision 0.848; recall 0.509; F1 0.636; TP 28; FP 5; FN 27.

- Reviewed all 32 current prediction errors and documented false-positive and false-negative patterns.

- Main improvement candidate: targeted identity-theft rule refinement without weakening Trigger 4.

- No labels, rules, definitions, or evaluation outputs changed.

- Output: `results/risk_error_analysis_v0.md`



### Task 2.5 — Freeze contextual risk rules v1 (2026-11-05)



- Decision: freeze the existing context-aware rules without further edits.

- Source: `src/complaintiq/risk.py`

- Frozen development baseline: 300 labels; 55 positives.

- Precision: 0.848; recall: 0.509; F1: 0.636; accuracy: 0.893.

- Confusion counts: TP 28; FP 5; FN 27.

- Verified `risk_dev_eval_v0.json` and `risk_rules.json` contain matching metrics.

- Known limitation: recall remains low; identity-theft and legal-threat misses are documented in the error-analysis report.

- No evaluation rerun.

- Output: `results/risk_dev_eval_v0.json`; error analysis: `results/risk_error_analysis_v0.md`



### Task 2.6 ? Label fresh temporal test set (2026-11-05)



- Completed and validated 250 independent temporal-holdout annotations.

- Labels: 60 positive; 190 negative.

- Complaint IDs and narratives preserved; severity left blank; positive or uncertain cases have notes.

- Sample date range: 2025-09-24 to 2026-07-14.

- Output: `results/risk_test_labels_250_v1.csv`



### Task 2.7 ? Risk flags temporal test report (2026-11-05)



- Evaluated frozen contextual rules v1 against the 250 labelled temporal test complaints.

- Precision: 0.909; recall: 0.167; F1: 0.282; accuracy: 0.796.

- Confusion counts: TP 10; FP 1; FN 50; TN 189.

- Test recall is substantially below development recall (0.509); rules remain unchanged.

- Output: `results/risk_flags_report_v1.md`; metrics: `results/risk_test_eval_v1.json`





### Task 3.1 ? Embedding speed benchmark (2026-11-05)



- Set SentenceTransformer maximum sequence length to 256.

- BGE-small: 2,000 narratives; model load 66.04s; embedding 204.29s; 9.79 rows/sec; projected 100k runtime 2.84 hours.

- MiniLM: 2,000 narratives; model load 19.05s; embedding 101.82s; 19.64 rows/sec; projected 100k runtime 1.41 hours.

- Both CPU models exceed the one-hour target. Local CUDA is unavailable; Kaggle GPU required.

- No full embedding build launched.



### Task 3.2 ? Resumable embedding implementation



- Verified existing `_encode_resumable()` in `src/complaintiq/pipeline.py`.

- Writes durable 2,000-row chunks to a memory-mapped NumPy array.

- Saves progress and validates model/data fingerprint, row count, dimensions and chunk size before resuming.

- Moves completed vectors into `vectors.npy` and removes the progress file.

- Implementation verified by code inspection; interruption/resume execution test remains outstanding.





### Task 3.3 ? Reproduce hashing baseline under frozen cutoff (2026-11-05)



- Reused existing full-data hashing artifact: `artifacts/complaintiq_full_hashing`.

- Frozen cutoff: 2025-09-24; training rows: 826,324; test rows: 229,940.

- Test IDs: 229,940 unique IDs.

- Sorted test-ID SHA256 matches manifest: `4bfc116b97595b9fbe9994ecac3b66d9926c6955907620c6f658f61b88f35b4a`.

- Existing evaluation: macro-F1 0.5131; weighted-F1 0.6602; accuracy 0.6355.

- Existing artifact and evaluation metadata agree on the frozen temporal split. No rebuild or evaluation rerun.





### Task 3.4 ? Full-data hashing classifier (2026-11-05)



- Reused existing `artifacts/complaintiq_full_hashing` artifact; no retraining.

- Verified classifier (`clf.joblib`), metadata (`meta.joblib`), vectors (`vectors.npy`), manifest and test IDs are present.

- Training rows: 826,324; test rows: 229,940; frozen cutoff: 2025-09-24.

- Existing evaluation metrics: macro-F1 0.5131, weighted-F1 0.6602, accuracy 0.6355.

- Verified sorted test-ID SHA256 against manifest.





### Task 3.5 ? MiniLM embedding evaluation (2026-11-05)



- Built full temporal artifact using MiniLM: `artifacts/complaintiq_full_minilm`.

- Training: 100,000 complaints; temporal test: 229,940 complaints.

- Test cutoff: 2025-09-24; test-ID SHA256 matches frozen manifest.

- Embedding dimensions: 384.

- Test macro-F1: 0.6321.

- Embedding runtime: 20,146.8 seconds (~5.60 hours).

- BM25 build: 46.82 seconds.

- All 329,940 embeddings completed successfully; no rerun required.

- Note: compare against hashing with the same 100k training sample before claiming a model improvement.





### Task 3.6 ? Classifier comparison (2026-11-05)



- Created `docs/classifier_comparison.md`.

- Compared 100k hashing (macro-F1 0.4909) against MiniLM (0.6321).

- Both use 100,000 training rows, 229,940 test rows, cutoff 2025-09-24 and identical test-ID SHA256.

- MiniLM improvement: +0.1412 absolute macro-F1 (~28.8% relative).



### Task 3.7 ? Confidence threshold validation (2026-11-05)



- Created `results/confidence_threshold_validation_v1.json` and `results/confidence_threshold_validation_v1.md`.

- Reused existing MiniLM embeddings; stratified 80/20 split of the 100,000 training rows (80,000 fit / 20,000 validation; random state 42).

- Selected initial operating threshold: **0.70**.

- Validation coverage: **62.5%**; accuracy among covered predictions: **87.6%**; escalation rate: **37.5%**.

- Frozen temporal test set was not used for threshold selection.

- Decision is provisional; validation is a random training-period split, not a later-period temporal validation.



### Task 4.1 - Retrieval leakage controls (2026-11-05)



- Verified `src/complaintiq/evals/retrieval.py` uses training-split documents only and removes duplicate normalized narrative templates from the index.

- Enforces a strict temporal holdout; excludes shared boundary-date rows, cross-split template matches, and duplicate test templates.

- Evaluation evidence: 53,883 indexed documents; 13,392 strictly later test rows before template exclusions; 300 sampled queries.

- Relevance remains a weak product/issue-match proxy, not human-judged precedent relevance.



### Task 4.2 - Retrieval cross-encoder ablation (2026-11-06)



- Evaluated real `cross-encoder/ms-marco-MiniLM-L-6-v2` on RRF top-50 candidates.

- Reused the exact 300 temporal queries; query-ID SHA256 matched the baseline.

- Preserved original BM25, dense and RRF metrics; reranker-only output saved separately.

- Created `docs/retrieval_cross_encoder_ablation.md`.

- RRF + cross-encoder: Hit@10 0.8067, nDCG@10 0.3458; RRF: 0.7700 and 0.3154.

- CPU search p50 increased from 13.711 ms to 9,462.421 ms; retain RRF as practical CPU default.

- Weak product/issue proxy labels are not human-judged precedent relevance.



### Task 4.3 - Retrieval top-1 relevance review (2026-11-07)



- Reviewed 50 RRF query-to-top-1 pairs from the frozen temporal query sample.

- Copilot-assisted judgments: 36 relevant, 10 not relevant, 4 uncertain.

- Decisive human relevance: 78.26% (36/46); uncertain cases excluded.

- All 50 rows have reviewer notes; original review sample preserved.

- Created `docs/retrieval_human_review_v1.md`.

- Assessment is assisted, not independent expert validation.



### Task 4.4 - Retrieval ablation decision (2026-11-07)



- Consolidated BM25, dense, RRF and real cross-encoder results in `docs/ablation.md`.

- Selected RRF as the practical CPU default; BM25 remains the low-latency baseline.

- Cross-encoder improves weak-proxy ranking metrics but costs approximately 690.1x RRF search p50 latency.

- Included the 50-pair Copilot-assisted review: 36 yes, 10 no, 4 uncertain; 78.26% among decisive judgments.

- Documented temporal leakage controls, proxy-label limitations and CPU-only latency caveats.



### Phase 5.1?5.2 ? Real Gemini validation and pricing (2026-11-07)



- Selected `gemini-3.1-flash-lite`; successfully completed a real five-complaint held-out evaluation using Gemini API, not MockLLM.

- Five-record smoke-test LLM-only macro-F1 was 1.000; this sample is too small for a quality claim. Observed LLM-only latency was 8,614.7 ms per complaint.

- Google Gemini API Standard paid-tier list prices for this model: $0.25 per 1M text input tokens and $1.50 per 1M output tokens. Free-tier pricing is separately listed; project estimates use paid-tier list prices and are not actual billed spend.

- Source: https://ai.google.dev/gemini-api/docs/pricing (accessed 2026-11-07); model details: https://ai.google.dev/gemini-api/docs/models/gemini-3.1-flash-lite.

- Updated `CIQ_PRICE_IN_PER_M` and `CIQ_PRICE_OUT_PER_M` defaults to `0.25` and `1.50`, respectively.





## Phase 5: 300-complaint cascade evaluation



- Sample: 300 held-out later-in-time complaints.

- LLM provider: Gemini; final selected model: gemini-3.5-flash-lite.

- Models used during fallback: gemini-3-flash-preview, gemini-3.1-flash-lite, gemini-3.1-flash-lite-preview, gemini-3.5-flash-lite.

- Classifier-only macro-F1: 0.456.

- LLM-only macro-F1: 0.694; estimated $0.1150 per 1,000 complaints.

- Cascade threshold 0.70: macro-F1 0.666; escalation rate 51.7%; estimated $0.0570 per 1,000 complaints.

- Pricing assumption: all recorded tokens priced at Gemini 3.5 Flash-Lite Standard rates ($0.30/M input, $2.50/M output). Per-call model attribution was not saved, so costs are estimates, not exact billed costs.

- Processing: batches of 10 with resumable checkpoint; 300/300 completed.





## Phase 6 ? Spike detection and alert review



- Evaluated 2,004,605 complaint records across 124 weeks; detector flagged 139 alerts.

- Reviewed the top 15 alerts using complaint narratives: 12 showed sample-level thematic support; 3 were mixed or weakly supported.

- No incident was independently confirmed by this qualitative review.

- Investigated the January 2025 synchronized surge. No duplicate complaint IDs or submission-channel shift explained it.

- Found substantial repeated narrative-template concentration in the Block alert; documented the counts and query-scope distinctions in `docs/spikes.md`.

- Classification: unexplained synchronized reporting-volume surge, with a plausible but unconfirmed reporting/campaign effect.

- Limitations include missing forwarding dates and absence of independently labeled incidents.

- Full report: `docs/spikes.md`.


## Phase 7 ? Drafter and Guardrails

- Five focused guardrail checks passed; see `docs/guardrail_checks.md`.
- 50-complaint temporal evaluation: 49 successful drafts, 1 refusal.
- Citation coverage, cited-precedent coverage, and exact-template validation: 100% each.
- Unsupported factual fields detected: 0; LLM generation calls: 0.
- Draft latency p50/p95: 23.726 / 60.638 ms.
- Relevance review: 150 precedents across 30 drafts; mean 2.340/3; 55.3% strongly relevant; 23.3% partially relevant; 21.3% irrelevant.
- 29/30 drafts had at least one strongly relevant precedent.
- Relevance ratings were assistant-assisted, not independent human validation.
- Drafter is deterministic/template-generated, not model-generated; it produces historical evidence summaries for human review.
- Detailed results: `docs/draft_evaluation.md`; guardrails: `docs/guardrail_checks.md`.


## Phase 8 ? API, UI, Docker and load testing

- API smoke tests passed; UI workflow verified, including fraud-risk human-review routing.
- Docker Compose API and Streamlit UI started; both health endpoints returned HTTP 200.
- Three 30-second Locust runs completed at 5, 10 and 20 concurrent users with zero failures.
- Aggregate p50/p95 latency: 5 users 87/610 ms; 10 users 320/2100 ms; 20 users 380/1100 ms.
- Throughput: 9.73, 10.23 and 24.37 requests/second, respectively.
- Benchmarks use the local Compose demo configuration (mock LLM, hashing embeddings, lexical reranker), not Gemini + MiniLM.
- Detailed benchmark and limitations: `docs/load_test.md`.


## Phase 9 ? Scale and quantization

- Real CFPB MiniLM vectors benchmarked using a 25,000-vector training index and 50 later-period temporal holdout queries.
- Float32 exact baseline: 36.62 MB vector storage; recall@10 1.000.
- Int8: 9.16 MB; recall@10 0.982; p50/p95/p99 79.384/146.914/176.985 ms.
- Binary: 1.14 MB; recall@10 0.416; p50/p95/p99 14.326/23.073/30.865 ms.
- Binary + int8 rescore: 10.30 MB combined; recall@10 0.858; p50/p95/p99 11.427/13.688/20.479 ms.
- Benchmark completed in 7.6 seconds. Latency percentiles use only 50 queries and are not production SLOs.
- Int8 offers the strongest measured storage/recall trade-off; float32 remained faster on this local workload.
- Detailed methodology, limitations and results: `docs/scale.md`; raw output: `results/quantization_temporal.json`.
