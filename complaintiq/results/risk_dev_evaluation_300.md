# Hand-labeled risk-rule evaluation

Rule metrics are measured only on rows with hand-entered risk_flag labels.

* Labeled rows: 300; positive rows: 55
* Precision: 0.27; recall: 1.0; F1: 0.425; accuracy: 0.503
* Confusion counts: TP 55, FP 149, FN 0

## Per-rule metrics

| Rule | Triggered rows | Precision | Recall | F1 |
|---|---:|---:|---:|---:|
| legal_threat | 24 | 0.333 | 0.145 | 0.203 |
| regulator_mention | 35 | 0.371 | 0.236 | 0.289 |
| identity_theft_fraud | 92 | 0.511 | 0.855 | 0.639 |
| foreclosure_housing | 1 | 1.0 | 0.018 | 0.036 |
| vulnerable_consumer | 0 | 0.0 | 0.0 | 0.0 |
| discrimination | 0 | 0.0 | 0.0 | 0.0 |
| credit_reporting_violation | 138 | 0.203 | 0.509 | 0.29 |
| debt_validation | 20 | 0.15 | 0.055 | 0.08 |

## Severity breakdown

| Severity | Labeled | Risk positives | Rule flagged | Recall on positives |
|---|---:|---:|---:|---:|
| high | 0 | 0 | 0 | None |
| medium | 0 | 0 | 0 | None |
| low | 0 | 0 | 0 | None |
