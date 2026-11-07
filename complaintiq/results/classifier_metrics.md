# Classifier benchmark (held-out temporal split)

Data type: `real_cfpb`.
Data source: `F:\ai\genai-portfolio\complaintiq\data\processed`.
Embedder `hashing`, trained on the earliest 826,324 rows and tested on the latest 229,940 rows. Label: `product`.
Sampled rows: 1,056,264; rows after deduplication: 1,056,264.

* **Macro-F1:** 0.5131 across 11 classes
* **Macro-F1 (support >= 50):** 0.5131
* **Weighted-F1:** 0.6602
* **Accuracy:** 0.6355 (majority baseline: 0.287)
* **Expected calibration error:** 0.0432

## Confidence threshold

| Threshold | Auto-handled | Accuracy on auto-handled |
|---:|---:|---:|
| 0.0 | 100.0% | 0.6355 |
| 0.5 | 61.1% | 0.7919 |
| 0.6 | 47.8% | 0.8415 |
| 0.7 | 35.9% | 0.8785 |
| 0.8 | 23.6% | 0.9091 |
| 0.9 | 10.4% | 0.9328 |

## Per-class results

| Class | Precision | Recall | F1 | Support |
|---|---:|---:|---:|---:|
| Credit reporting or other personal consumer reports | 0.8505 | 0.7454 | 0.7944 | 65986 |
| Debt collection | 0.8029 | 0.6229 | 0.7015 | 47950 |
| Checking or savings account | 0.6809 | 0.5768 | 0.6246 | 32448 |
| Credit card | 0.6749 | 0.5644 | 0.6147 | 30829 |
| Money transfer, virtual currency, or money service | 0.5223 | 0.4955 | 0.5086 | 15492 |
| Mortgage | 0.6115 | 0.734 | 0.6672 | 11551 |
| Vehicle loan or lease | 0.4292 | 0.6346 | 0.512 | 9135 |
| Payday loan, title loan, personal loan, or advance loan | 0.2772 | 0.438 | 0.3395 | 6582 |
| Student loan | 0.4687 | 0.7098 | 0.5646 | 5902 |
| Prepaid card | 0.1432 | 0.5846 | 0.2301 | 2410 |
| Debt or credit management | 0.0504 | 0.3166 | 0.087 | 1655 |
