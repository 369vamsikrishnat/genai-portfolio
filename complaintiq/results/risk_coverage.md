# Risk-rule coverage audit

Coverage describes how often rules trigger. Without hand labels it does not measure precision, recall, correctness, or calibrated priority.

Source: `F:\ai\genai-portfolio\complaintiq\data\processed` (real_cfpb). Temporal holdout: 13,491 rows, 2025-09-23 to 2026-07-29.
Rules flagged 5,576 rows (41.3%).

## Trigger coverage by rule

| Rule | Rows | Holdout rate |
|---|---:|---:|
| legal_threat | 729 | 5.4% |
| regulator_mention | 1,801 | 13.4% |
| identity_theft_fraud | 3,975 | 29.5% |
| foreclosure_housing | 136 | 1.0% |
| vulnerable_consumer | 110 | 0.8% |
| discrimination | 67 | 0.5% |

## Trigger coverage by product

| Product | Rows | Flagged | Flagged rate |
|---|---:|---:|---:|
| Checking or savings account | 1,627 | 802 | 49.3% |
| Credit card | 1,633 | 626 | 38.3% |
| Credit reporting or other personal consumer reports | 4,889 | 2,356 | 48.2% |
| Debt collection | 2,692 | 874 | 32.5% |
| Debt or credit management | 94 | 21 | 22.3% |
| Money transfer, virtual currency, or money service | 744 | 344 | 46.2% |
| Mortgage | 581 | 212 | 36.5% |
| Payday loan, title loan, personal loan, or advance loan | 362 | 100 | 27.6% |
| Prepaid card | 122 | 50 | 41.0% |
| Student loan | 280 | 73 | 26.1% |
| Vehicle loan or lease | 467 | 118 | 25.3% |

## Priority and validation gaps

* The current rules return categories, not an ordered or calibrated priority score.
* These unlabeled coverage counts cannot establish whether a flagged complaint is high priority.
* Hand-label representative temporal-holdout rows with `risk_flag` and severity, then run `eval-risk` to measure overall and per-rule performance.
