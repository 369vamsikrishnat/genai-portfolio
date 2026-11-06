# Retrieval top-1 human relevance review

- Reviewed pairs: 50
- Relevant: 36
- Not relevant: 10
- Uncertain: 4
- Human relevance among decisive judgments: **78.26%** (36/46)

## Method

Reviewed the top-1 RRF result for 50 queries sampled from the same frozen temporal query set used by the retrieval baseline. Copilot assisted the narrative comparison. Judgments considered the underlying dispute and usefulness as a potential precedent, not product/issue label agreement alone.

## Observations

Relevant pairs commonly shared the underlying dispute, including debt validation, inaccurate reporting, or unauthorized transactions, even when some details differed. Irrelevant pairs often shared only broad product labels while describing different problems. Uncertain cases had limited narrative detail or partial overlap.

## Limitations

- This was a Copilot-assisted assessment, not independent expert validation.
- The sample contains 50 query-to-top-1 pairs and should not be treated as a comprehensive relevance benchmark.
- Four uncertain judgments are excluded from the decisive relevance percentage.
- The original weak product/issue proxy evaluation remains unchanged.

## Artifacts

- Review sample: `results/retrieval_top1_review_50_v1.csv`
- Completed review: `results/retrieval_top1_review_50_v1_reviewed.csv`
