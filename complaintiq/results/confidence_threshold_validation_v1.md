# Confidence Threshold Validation v1

## Method
- MiniLM embeddings from the existing 100,000-row training sample.
- Stratified 80/20 split: 80,000 fit rows and 20,000 validation rows.
- Random state: 42.
- Logistic regression: C=10, max_iter=2000, class_weight=balanced.
- Frozen temporal test set was not used for threshold selection.

## Selected operating threshold
- Threshold: 0.70
- Validation coverage: 62.5%
- Accuracy among covered predictions: 87.6%
- Escalation rate: 37.5%
- Automatically handled: 12,510 / 20,000
- Escalated: 7,490 / 20,000

## Decision
Use 0.70 as the initial candidate operating threshold. It balances automatic coverage and accuracy better than the more conservative 0.90 threshold. This is a validation-only decision, not a production-readiness claim.

## Limitations
- Validation is a stratified random split of the training period, not a later-period temporal validation.
- Accuracy is measured only among predictions meeting the confidence threshold.
- Escalated cases require a defined downstream review or fallback path.
- Do not tune this threshold using the frozen temporal test set.

Detailed threshold metrics: `confidence_threshold_validation_v1.json`.
