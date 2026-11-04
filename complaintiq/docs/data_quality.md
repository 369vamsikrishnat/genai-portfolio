# Data-quality report

## Manual privacy review

- Sample: 100 randomly selected, template-deduplicated narratives (seed 42).
- Clearly visible, unmasked personal identifiers: 0 of 100.
- Phone, email, SSN and card-number checks: no matches.
- Finding: identifiers in the reviewed narratives appeared masked.
- Limitation: this is a 100-record spot-check, not proof of zero PII across the full dataset.
- Review file: `results/privacy_review_100.csv`.

Generated 2026-11-04. Computed on a 200,000-row deterministic sample.

* Rows analysed: **200,000**; dates 2024-04-01 to 2026-07-29
* Duplicate complaint IDs: **0** (must be 0)
* Template duplication: **34.8%** of narratives repeat another narrative (130,429 distinct). Index/eval de-duplicate these so retrieval is not rewarded for finding its own template twin.
* Narrative length (chars): {'p5': 127, 'p50': 671, 'p95': 2944, 'p99': 5780}; under 50 chars: 156
* Missing share: {'product': 0.0, 'issue': 0.0, 'company': 0.0, 'company_response': 0.0}
* Products: 11, issues: 87

## Top products

* Credit reporting or other personal consumer reports: 71.7%
* Debt collection: 9.8%
* Checking or savings account: 4.7%
* Credit card: 4.4%
* Money transfer, virtual currency, or money service: 4.1%
* Mortgage: 1.5%
* Vehicle loan or lease: 1.2%
* Student loan: 1.0%
* Payday loan, title loan, personal loan, or advance loan: 0.8%
* Prepaid card: 0.4%

## Rows by year

* 2024: 66,251
* 2025: 121,585
* 2026: 12,164

## PII check (after redaction)

* Rows still matching a PII pattern: {'ssn': 0, 'card': 0, 'email': 0, 'phone': 0, 'number': 0} (target: all 0)
* Rows containing our redaction tokens: 33; CFPB's own XXXX mask: 117,232
* Regexes cannot catch names/addresses in free text. Spot-read 100 random rows before publishing anything.

## Join coverage (from ingest)

* skipped: False
* rows: 2004605
* sha256: e94a24875bf31e2bd8f8d8bd0eeb4ba6932bdd594a1c19e347c7133c26371acd
* seconds: 1834.9
* archive_rows: 2004636
* archive_distinct_ids: 2004636
* archive_unmatched_ids: 31
* main_rows_in_scope: 14258591
* joined_rows: 2004605
* narrative_coverage_of_main: 0.1406
* distinct_narrative_hashes: 1056264
