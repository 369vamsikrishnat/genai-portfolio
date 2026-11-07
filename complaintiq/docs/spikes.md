# ComplaintIQ ? Spike Detection and Alert Review

## 1. Dataset coverage

Source: `data/processed/complaints`

- Weekly grouped rows: 225,706
- Company/product/issue groups: 26,730
- Weeks covered: 124 (2024-04-01 to 2026-08-10)
- Complaint records counted: 2,004,605
- Alerts generated: 139
- Top alerts reviewed: 15

Detector configuration:
- Trailing baseline: 8 weeks, excluding the current week
- Minimum current-week count: 10
- Minimum prior baseline count: 20
- Minimum observed baseline weeks: 4
- Multiple-testing correction: causal alpha spending

Severity is a statistical magnitude indicator, not a measure of consumer harm or verified incident severity.

## 2. January 2025 cluster investigation

The week beginning 2025-01-13 contains an unusually broad set of alerts across unrelated institutions and complaint categories.

Daily complaint totals:
- 2025-01-13: 4,006
- 2025-01-14: 5,076
- 2025-01-15: 10,064
- 2025-01-16: 10,514
- 2025-01-17: 20,524
- 2025-01-18: 12,967
- 2025-01-19: 5,255
- 2025-01-20: 8,804

For January 1?14, the dataset contains 45,338 complaints (3,239/day). During January 15?20 it contains 68,128 (11,355/day), approximately 3.5 times the earlier daily rate. January 21?February 2 contains 64,091 (4,930/day).

All three periods contain only Web submissions. No submission-channel change explains the increase. There are no repeated complaint IDs in any of the three periods.

The `date_sent_to_company` field is unavailable, so receipt dates cannot be compared with forwarding dates.

### Repeated narrative evidence

The Block alert for money-transfer/other-transaction-problem complaints contains 17,417 complaints and 5,610 distinct narrative hashes; 11,807 rows have a hash already represented elsewhere in that alert.

The most frequent hash in the alert occurs 8,042 times within the alert's company/product/issue/week grouping.

The repeated narrative is a legalistic Cash App complaint alleging inadequate fraud prevention and dispute resolution, referencing the CFPA, EFTA and Regulation E. A broader query found this hash across multiple Block complaint categories and a small number of other companies. The hash's most frequent narrative text appeared 7,764 times in the full dataset query; the hash appeared 12,227 times in the Block money-transfer/other-transaction-problem category across the full dataset.

For the January 13?19 period, a company-level daily query found 8,271 occurrences of this hash across Block categories:
- January 16: 543
- January 17: 4,893
- January 18: 2,156
- January 19: 679

The distinction between the alert-specific count and the broader company-level count is intentional: the latter query did not restrict product and issue.

Other alerts also show repeated text:
- Navy Federal: 2,050 repeated rows
- Experian: 1,480 repeated rows
- Early Warning Services, October 2025: 203 repeated rows

Identical narrative hashes do not imply duplicate complaint records. The complaint IDs were distinct. Repeated templates may reflect coordinated submissions, copied wording, campaigns, or other common influences; the dataset alone cannot establish which explanation is correct.

### Classification

**January 2025 cluster: unexplained synchronized reporting-volume surge, substantially amplified by repeated narrative templates in the Block alert.**

A bulk-reporting or campaign effect is plausible, but the underlying cause is unconfirmed. The surge should not be described as a confirmed single incident or dismissed as entirely false.

## 3. Top-15 narrative review

Two complaint narratives per alert were sampled where available. Review outcome:

- 12/15 alerts: sampled narratives support the broad complaint theme.
- 3/15 alerts: mixed or weak sample-level support.
- 0/15 alerts: independently confirmed incidents based on this review alone.

Examples of supported themes included:
- Cash App account compromise, unauthorized transfers, fraud and dispute handling
- Bank account restrictions, overdraft fees and account management
- Zelle payment disputes, scams and unauthorized transfers
- Student-loan servicing and borrower-defense complaints
- Credit-report investigation disputes

Some samples did not cleanly match their assigned taxonomy. In particular, the student-loan and report-use alerts included narratives about related but not identical issues; one Early Warning Services sample was about Zelle payments rather than credit reporting.

The narrative review is a qualitative sample, not a representative audit of every complaint in each alert. Sample-level thematic support does not prove a new incident, causal relationship, or company-wide failure.

## 4. Evaluation limitations

- No independently labeled incident dataset was available to calculate false-alert rate or precision.
- Detection latency cannot be measured without incident-onset labels.
- CFPB complaint arrival and publication patterns may create bursts unrelated to new underlying incidents.
- Repeated narrative templates can amplify counts.
- The dataset does not include `date_sent_to_company`.
- Statistical severity is not consumer-harm severity.
- This is a descriptive historical backtest, not proof of predictive accuracy.

## 5. Conclusion

The detector surfaced statistically unusual complaint-volume patterns across the available 2024?2026 dataset. Narrative sampling supported the broad themes of most top alerts, while the January 2025 investigation exposed substantial repeated-template concentration in the largest Block alert.

The system should present these outputs as **review-priority alerts**, not confirmed incidents. Human investigation and external corroboration remain necessary before escalation or public claims.
