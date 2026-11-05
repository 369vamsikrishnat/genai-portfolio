# ComplaintIQ ? Risk Flags Evaluation Report v1

## Evaluation design
- Frozen contextual rules: `src/complaintiq/risk.py`
- Risk definition: `RISK_DEFINITION.md` (unchanged)
- Development set: 300 labelled complaints; 55 positives.
- Independent temporal test sample: 250 complaints; 60 positives and 190 negatives.
- Test sample dates: 2025-09-24 to 2026-07-14.
- Test annotations were completed before evaluation. Complaint IDs and narratives were preserved.
- No rule changes or test-set tuning were performed.

## Results

| Metric | Development | Temporal test |
|---|---:|---:|
| Labelled complaints | 300 | 250 |
| Actual positives | 55 | 60 |
| Precision | 0.848 | 0.909 |
| Recall | 0.509 | 0.167 |
| F1 | 0.636 | 0.282 |
| Accuracy | 0.893 | 0.796 |

### Temporal test confusion counts
- True positives: 10
- False positives: 1
- False negatives: 50
- True negatives: 189

## Findings
The frozen rules maintain high precision on the temporal test sample (0.909), but recall is low (0.167). They detected only 10 of 60 labelled risk-positive complaints and missed 50. This is a significant recall decline compared with the development set.

The rules are conservative: flagged complaints are usually positive, but many positive complaints are not flagged. Accuracy alone would obscure this limitation.

## Limitations and decision
- The test evaluation is based on a 250-complaint sample from the saved temporal holdout, not the entire 13,491-row holdout.
- Results depend on the annotation quality and the frozen risk definition.
- Severity was intentionally left blank and was not evaluated.
- The test set must remain untouched for future rule tuning.
- Keep contextual rules v1 frozen. Investigate missed-risk patterns using a separate development/tuning dataset before considering a new version.

## Reproducibility
- Labels: `results/risk_test_labels_250_v1.csv`
- Test metrics: `results/risk_test_eval_v1.json`
- Development baseline: `results/risk_dev_eval_v0.json`
- Error analysis: `results/risk_error_analysis_v0.md`
