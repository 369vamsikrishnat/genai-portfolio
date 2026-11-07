# ComplaintIQ Guardrail Checks

Five focused guardrail checks executed against the current implementation.

| Check | Result |
|---|---|
| Prompt-injection blocking | PASS |
| Input sanitization | PASS |
| Insufficient-evidence refusal | PASS |
| Citation and historical-context validation | PASS |
| Unsupported-prose rejection | PASS |

## Drafter implementation

The current drafter is deterministic and template-generated. It does not call an LLM.
`build_prompt()` exists as prompt construction code but is not used by the production draft path.
The `llm` constructor argument is not invoked by `Drafter.draft()`.

The output reports retrieved historical CFPB product, issue, and company-response categories.
It explicitly states that historical records do not establish the facts or outcome of the current complaint.
A human reviewer is required before a substantive response is sent.

## Scope and limitations

These checks exercise the current code paths; they are not a penetration test or legal review.
Exact-template validation checks output integrity, not semantic entailment or factual correctness of source records.
