# Day 36 — proposed MergeGuard demo storyboard

**Status:** This is a proposed recording script, not a recorded walkthrough. No PR, live dashboard, or metric screenshot is supplied by this document. Record only against a configured local instance and identify any synthetic fixture as synthetic.

## Target runtime

About 90 seconds.

## Suggested recording flow

### 0:00–0:12 — Introduce the workflow

Show the repository README and the LangGraph path from PR intake through review agents to a verdict. Avoid presenting a sample PR or result as real unless it was actually run.

### 0:12–0:30 — Show the tool boundaries

Show the privilege table in the README or `docs/mcp.md`: Code-Analysis has GitHub read tools, Test-Execution has `run_tests(job_id)`, and Security has GitHub read tools plus dependency scanning. The allowlists and schemas are covered by `tests/mcp/test_protocol_and_allowlists.py`.

### 0:30–0:48 — Show test execution behavior

If the local Compose stack is running, demonstrate the sandbox service configuration and an actual job result. The sandbox is configured with `network_mode: none` and a read-only workspace mount. Do not claim that PR dependencies are installed in the no-network sandbox. If tests cannot import dependencies, the expected status is `error`; show the recorded reason and human-review requirement rather than describing it as a test pass or automatic block.

### 0:48–1:05 — Show human review state

Use a test-backed or genuinely executed job that is actually awaiting review. Show the review endpoint's authenticated request and its `review_queued` response only if performed during recording. Do not narrate queue acceptance as proof that graph resumption has completed; use the later `/pr/{job_id}/status` result to establish completion.

### 1:05–1:22 — Show measurements only when available

Use a timestamped report from `eval/results/` for golden-set measurements and a live `/metrics` response for operational metrics. If either source is unavailable, say that the measurement has not yet been collected; do not fill the gap with example numbers.

### 1:22–1:30 — State deployment scope

Close by saying the repository contains a local Docker Compose configuration. MergeGuard is not deployed to Cloud Run.

## Voiceover draft

“MergeGuard is a pull-request review workflow with separate code-analysis, test-execution, and dependency-review responsibilities. Its agents call constrained MCP tools, and the test runner delegates by job ID to a no-network sandbox. The graph combines structured findings into a verdict and pauses for human review when its rules require it. The golden PR set is empty until human reviewers label real examples, so I report no evaluation accuracy yet. This project is configured for local Docker Compose use and is not deployed to Cloud Run.”

## Recording checklist

- Confirm API, Redis, worker, and sandbox services are actually available before showing runtime behavior.
- Use real PR content only when authorized; label any fixture as synthetic.
- Show only terminal output or API responses observed during the recording.
- Use numbers only when copied from a test run, an `eval/results/*.json` file, or the `/metrics` endpoint.
- Do not describe `review_queued` as completed resumption; verify the resulting job status.
