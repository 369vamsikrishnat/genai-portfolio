# Risk Rule Error Analysis — Development Set

Date: 2026-11-05
Dataset: results/risk_dev_labels_300_v1.csv
Evaluation: results/risk_dev_eval_v0.json

## Baseline

- Labelled complaints: 300
- Positive labels: 55
- True positives: 28
- False positives: 5
- False negatives: 27
- Precision: 0.848
- Recall: 0.509
- F1: 0.636
- Accuracy: 0.893

## False-negative investigation

All 27 false negatives were extracted by comparing current rule predictions against frozen labels.

Keyword investigation found overlapping patterns:
- Fraud, scam, theft or stolen wording: 21
- Fraudulent or unauthorized accounts: 13
- Identity-theft wording: 7
- Data-breach wording: 7
- Accounts opened without permission: 6

These counts overlap and are not additive.

Several missed examples describe accounts allegedly opened without authorization, fraudulent accounts, identity theft, or fraudulent transactions. These are candidates for closer review against Trigger 4.

A data breach or an unfamiliar/inaccurate account alone must not qualify. The definition requires an allegation that someone else opened or used an account in the consumer's name, took over an account, or took money by fraud.

## False-positive investigation

Five false positives were identified:

| Complaint ID | Preliminary finding |
|---|---|
| 17239078 | Additional student-loan payment; no clear identity theft |
| 14258648 | Data breach and inaccurate accounts; actual third-party account opening not established in the shown text |
| 13880922 | Identity-theft report and account reinsertion; actual fraudulent opening/use not established in the shown text |
| 13257185 | Statutory deadline allegation; specific missed legal deadline needs verification |
| 10125671 | Merchant debit dispute involving another party; identity theft not established |

## Rule-level observations

- legal_threat: precision 1.000, recall 0.109
- identity_theft_fraud: precision 0.840, recall 0.382
- foreclosure_housing: precision 1.000, recall 0.018
- regulator_mention, vulnerable_consumer and discrimination: zero detections in this development sample
- missed_statutory_deadline: one detection, with zero precision

Zero detections do not establish that a rule is defective; the sample may not contain qualifying examples.

## Decision

Do not broaden rules to match generic words such as unauthorized, inaccurate, data breach, or fraud without the contextual evidence required by the frozen definition.

The identity-theft rule is the main candidate for targeted improvement, but changes must preserve the Trigger 4 boundary and be evaluated against the same frozen development labels.

No labels, definitions, rules, or evaluation outputs were changed during this analysis.

## Limitation

This is a preliminary error analysis based on the displayed narrative extracts and current rule matches. Ambiguous cases require full-text human review before any rule change or label reassessment.
