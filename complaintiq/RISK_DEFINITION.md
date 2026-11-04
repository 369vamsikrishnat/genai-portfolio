# ComplaintIQ Risk Label Definition

A complaint is risk-positive (1) when the text itself states facts showing a credible need for priority review beyond routine handling, because of one of these triggers.

## Trigger 1 — Escalation beyond this complaint

The consumer states an intent to take legal action, hire an attorney, or report the matter to a regulator, state attorney general, or other agency. Merely saying the complaint was filed with the CFPB, quoting a law, or describing a past lawsuit does not count.

A stated or conditional intent ("I will," "I plan to," "if not resolved I will") counts. Reserving rights or noting that legal action "may" be possible, with no stated intent, does not.

## Trigger 2 — Alleged discrimination

The consumer explicitly alleges that the company discriminated against them.

## Trigger 3 — Vulnerable consumer

The consumer states they are elderly, a servicemember or veteran, or disabled, and describes financial harm or exploitation caused by the company's alleged conduct. Vulnerable status alone, or an adverse outcome not tied to the company's conduct, does not count.

## Trigger 4 — Actual fraud or identity theft with harm

The consumer states that someone else opened or used an account in their name, took over an account, or took their money by fraud. An unfamiliar or inaccurate account, with no such allegation, does not count. A reference to an identity-theft report strengthens the case but isn't required.

## Trigger 5 — Imminent loss of housing

The text states an eviction notice, a notice of default or intent to foreclose, a foreclosure filing, a sale date, a lockout, or a stated deadline. General fear of foreclosure, and routine loss-mitigation or options letters, do not count.

## Trigger 6 — Missed statutory deadline

A missed deadline counts only if the consumer ties it to a legal or regulatory requirement (for example, "the 30-day legal limit") and the response or investigation is still outstanding. A bare elapsed-time complaint does not count.

## Negative-label rule

Everything else is negative (0), including ordinary disputes about credit reports, payment history, account servicing, debt validation, or slow follow-up. Label only from what the text states; do not infer. If a trigger is unclear, label 0 and write a note.

Severity is an unscored descriptive field.

## Consistency anchors

These examples are outside the original 250-row labelled dataset. They are consistency anchors only, not development or test observations and not rule-tuning examples.

| Complaint ID | Label | Rationale |
|---|---:|---|
| 10958705 | 1 | Veteran alleges discrimination; trigger 2 |
| 15855704 | 1 | Explicit discrimination allegation |
| 14513791 | 1 | Actual identity theft and unauthorized accounts |
| 11553972 | 0 | CFPB lawsuit mentioned; no personal escalation intent |
| 10958705 | 1 | Discrimination allegation; trigger 2, not trigger 3 |
| 13202679 | 0 | Elapsed time without a specifically identified legal deadline |
| 10336198 | 1 | Conditional intent to pursue legal action |
| 10336024 | 1 | Explicit intent to bring legal action |
| 10380544 | 0 | Legal provisions cited; no stated intent to escalate |
| 10588215 | 1 | Explicit eviction notice |
| 10457410 | 0 | Pre-foreclosure options letter; no qualifying notice, filing, sale date, lockout, or stated deadline in the reviewed narrative |

## Evaluation limitation

The legal-escalation trigger uses explicit stated or conditional intent. This improves consistency but may miss genuine threats expressed only in hedged language. Template language may also cause this trigger to fire frequently. Measure its positive rate on the development set; if it exceeds approximately 30%, review whether the intent is directed at the company or another named party before considering any definition change.
