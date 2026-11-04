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
