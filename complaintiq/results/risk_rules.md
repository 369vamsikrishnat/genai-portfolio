# Hand-labeled risk-rule evaluation

Rule metrics are measured only on rows with hand-entered risk_flag labels.

* Labeled rows: 300; positive rows: 55
* Precision: 0.848; recall: 0.509; F1: 0.636; accuracy: 0.893
* Confusion counts: TP 28, FP 5, FN 27

## Per-rule metrics

| Rule | Triggered rows | Precision | Recall | F1 |
|---|---:|---:|---:|---:|
| legal_threat | 6 | 1.0 | 0.109 | 0.197 |
| regulator_mention | 0 | 0.0 | 0.0 | 0.0 |
| identity_theft_fraud | 25 | 0.84 | 0.382 | 0.525 |
| foreclosure_housing | 1 | 1.0 | 0.018 | 0.036 |
| vulnerable_consumer | 0 | 0.0 | 0.0 | 0.0 |
| discrimination | 0 | 0.0 | 0.0 | 0.0 |
| missed_statutory_deadline | 1 | 0.0 | 0.0 | 0.0 |

## Severity breakdown

| Severity | Labeled | Risk positives | Rule flagged | Recall on positives |
|---|---:|---:|---:|---:|
| high | 0 | 0 | 0 | None |
| medium | 0 | 0 | 0 | None |
| low | 0 | 0 | 0 | None |
