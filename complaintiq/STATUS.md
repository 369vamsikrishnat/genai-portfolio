# ComplaintIQ — Project Status

## Phase 0: Setup

Commits: `74fac87`, `b3d3732`

- [ ] 0.1 Clean the repo — verify no sensitive paths, data, artifacts or `.env` files are tracked.

## Phase 1: Data

Commits: `74fac87`, `b3d3732`

- [ ] 1.1 Review 100 random narratives for missed PII; record the count and examples in `docs/data_quality.md`.

## Phase 2: Risk Flags

- [x] 2.1 Label the 300 development rows
- [x] 2.2 Freeze the labels — commit `8cefcda`
- [x] 2.3 Score current rules against frozen labels
- [x] 2.4 Error analysis
- [x] 2.5 Contextual rule edits and freeze — commit `6507f37`
- [x] 2.6 Label fresh temporal test set (250 rows)
- [x] 2.7 Evaluate frozen rules and write risk flags report — commit `9aa180a`

## Phase 3: Classifier Comparison

- [ ] 3.1 Fix embedding speed; complete 2,000-narrative timing test
- [x] 3.2 Make embedding resumable if processing takes over one hour (existing implementation inspected; runtime resume test pending)
- [x] 3.3 Reproduce hashing baseline under frozen cutoff (existing artifact and sorted test-ID hash verified)
- [x] 3.4 Full-data hashing artifact, metrics and test-ID hash verified (existing outputs reused)
- [x] 3.5 Run embedding model on the same sample and test set
- [x] 3.6 Create `docs/classifier_comparison.md`
- [x] 3.7 Select confidence threshold on validation data, not test data (stratified 80/20 training split; selected 0.70; validation coverage 62.5%, covered accuracy 87.6%; temporal test untouched)

## Phase 4: Retrieval

- [x] 4.1 Confirm index uses deduplicated narratives and evaluation excludes same-hash matches
- [x] 4.2 Run BM25, dense, RRF and RRF with real cross-encoder ablation
- [x] 4.3 Review 50 query-to-top-1 pairs and record relevance percentage
- [x] 4.4 Write `docs/ablation.md` and identify the winner

## Phase 5: Cascade with a Real LLM

- [x] 5.1 Choose an LLM suitable for available hardware; validate five complaints
- [x] 5.2 Record current provider prices, source and date in `RESULTS_LOG.md`
- [x] 5.3 Run classifier-only, LLM-only and cascade on 300 held-out complaints
- [x] 5.4 Apply Phase 3.7 threshold and report escalation rate, F1 and estimated cost per 1,000
- [x] 5.5 Write `docs/cost_table.md` with estimated costs clearly labelled

## Phase 6: Spike Alerts

- [x] 6.1 Run detection on the widest available dataset and report coverage
- [x] 6.2 Investigate the 2025-01-13 cluster and classify its cause
- [x] 6.3 Review examples for the top 15 alerts
- [x] 6.4 Write `docs/spikes.md` reporting how many of 15 alerts were verified

## Phase 7: Drafter and Guardrails

- [x] 7.1 Complete and record all five guardrail hand checks in `docs/guardrail_checks.md`
- [x] 7.2 Run 50 test complaints through the drafter and record status and quality metrics
- [x] 7.3 Hand-rate 30 drafts for precedent relevance
- [x] 7.4 Clearly identify whether the drafter is model-generated or templated

## Phase 8: API, UI and Docker

- [x] 8.1 Complete API smoke tests for health, triage, draft, blank input and wrong API key
- [x] 8.2 Verify UI end-to-end and save a screenshot
- [x] 8.3 Verify Docker Compose services start and `/health` responds
- [x] 8.4 Load test at three concurrency levels and record p50 and p95

## Phase 9: Scale

- [x] 9.1 Run quantization ladder on real temporal-holdout vectors; document measured memory, recall and latency in `docs/scale.md`

## Phase 10: Write-up
- [x] 10.1 Complete final audit for unexplained WARNING, simulated, mock and F:\ai references; check tracked file sizes
- [x] 10.2 Complete README with problem, architecture, result tables and limitations
- [ ] 10.3 Record and link two-minute demo video
- [x] 10.4 Write resume bullets using measured, traceable results only
- [x] 10.5 Complete interview-readiness check
- [ ] 10.6 Complete portfolio README, tag `v1.0` and push
