# Day 37 — draft LinkedIn and resume copy

This is portfolio copy about the code in this repository, not a claim of a production deployment or a recorded customer demonstration. Keep measurements tied to the sources named below.

## LinkedIn post draft

Building MergeGuard, a pull-request review workflow with explicit tool boundaries:

- Code-Analysis uses GitHub read tools.
- Test-Execution calls a fixed `run_tests(job_id)` tool that delegates to a no-network sandbox.
- Security uses GitHub read tools and a dependency-scanning tool.

The MCP servers use the official Python SDK; per-agent allowlists restrict which tools each role may call. The LangGraph workflow combines structured findings and test results. When its policy requires human review, the graph pauses; the API queues a submitted decision and the worker resumes the graph.

The latest local test-suite run reported **115 passed in 54.93s**. The golden PR evaluation set is empty until human reviewers label real PRs, so I do not report evaluation accuracy. MergeGuard is not deployed to Cloud Run.

## Resume bullets

- Implemented a LangGraph pull-request review workflow that combines code-analysis, test-execution, and dependency-scan results into structured verdicts.
- Added official MCP SDK stdio servers with per-agent tool allowlists for GitHub reads, sandbox test delegation, and dependency scanning.
- Isolated test execution behind a job-ID interface and a Docker Compose sandbox configured without network access; missing dependencies are reported as inability to run tests, not as an automatic blocking verdict.
- Implemented Redis-backed job queueing, authenticated webhook intake, human-review checkpoints, persisted run data, and API endpoints for status and operational metrics.
- Added a human-populated golden PR evaluation harness; no accuracy result is claimed while its labeled dataset is empty.

## Short interview summary

“I built MergeGuard as a pull-request review workflow with separate roles for code analysis, test execution, and dependency review. The roles use constrained MCP tools, and repository tests are delegated to a no-network sandbox rather than run by the review agent. The graph can pause for human review and records submitted decisions through the API and worker. The latest local test run reported 115 passed in 54.93 seconds. I have not populated the human-labeled golden PR set, so I do not have an accuracy number to report, and the project is not deployed to Cloud Run.”

## Evidence references

- Workflow, API, and review checkpoint: [`workflow/graph.py`](../src/mergeguard/workflow/graph.py), [`api/app.py`](../src/mergeguard/api/app.py), [`worker/main.py`](../src/mergeguard/worker/main.py)
- MCP server and allowlist tests: [`mcp_servers/`](../src/mergeguard/mcp_servers/), [`test_protocol_and_allowlists.py`](../tests/mcp/test_protocol_and_allowlists.py)
- Sandbox and no-network behavior: [`docker-compose.yml`](../docker-compose.yml), [`test_result_classification.py`](../tests/sandbox/test_result_classification.py)
- Operational metrics implementation: [`observability/metrics.py`](../src/mergeguard/observability/metrics.py); collect actual values from `/metrics` before quoting them.
- Golden PR evaluation: [`eval/README.md`](../eval/README.md); quote accuracy only from a generated file in `eval/results/`.
