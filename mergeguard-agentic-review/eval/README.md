# Golden PR Evaluation

`golden_prs.json` intentionally starts empty. A human reviewer must select and label 20 real pull requests before the evaluation has a meaningful result. Do not add fabricated PRs, expected verdicts, or result numbers.

The file schema is a JSON array of objects with these fields:

```json
[
  {
    "owner": "real-github-owner",
    "repo": "real-repository",
    "pr_number": 123,
    "expected_verdict": "MERGE",
    "rationale": "Human-written explanation for the expected verdict."
  }
]
```

Allowed expected verdicts are `MERGE`, `MERGE_WITH_COMMENTS`, and `BLOCK`. The example above documents the schema only and is not a golden-set entry.

Run from the project root with the local services, GitHub credentials, Gemini settings, and sandbox runner configured:

```powershell
python scripts/run_golden_eval.py --no-human
```

Each real PR is passed through the worker pipeline with human interruption disabled for evaluation. Results are written under `eval/results/` with a UTC timestamp. Only quote evaluation metrics that appear in a committed or otherwise verified results file; an empty golden set produces null accuracy and `null` precision/recall values for every class.