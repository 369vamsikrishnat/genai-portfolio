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
