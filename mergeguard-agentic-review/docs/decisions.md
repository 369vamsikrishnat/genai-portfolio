# MergeGuard architecture decisions

This log records design decisions that are implemented in the repository. Test and runtime measurements are not inferred from design intent; see the README's measured-results table for values that still need to be collected.

## ADR-01: separate review responsibilities and tool privileges

**Status:** Accepted

Code review, test execution, and dependency scanning are separate graph nodes and separate MCP tool surfaces.

**Consequences:**

- Code-Analysis can call GitHub read tools only.
- Test-Execution can call the fixed `run_tests(job_id)` tool only.
- Security can call GitHub read tools and `scan_dependencies`.
- The graph combines structured findings and test results into a verdict.

**Evidence:** [`agents/mcp_client.py`](../src/mergeguard/agents/mcp_client.py), [`mcp_servers/`](../src/mergeguard/mcp_servers/), [`workflow/graph.py`](../src/mergeguard/workflow/graph.py), and [`test_protocol_and_allowlists.py`](../tests/mcp/test_protocol_and_allowlists.py).

## ADR-02: run PR tests in a no-network sandbox

**Status:** Accepted

PR source code is untrusted. The worker stages source into a workspace and requests tests by job ID; the sandbox runner executes the fixed pytest command in a separate service configured without network access.

**Consequences:**

- The test tool does not accept arbitrary commands or paths.
- The sandbox service has `network_mode: none`, mounts staged workspaces read-only, and has process and memory limits.
- Missing imports/dependencies in the sandbox are reported as a test `error`, not as a test failure that automatically blocks the PR. The graph retains a “tests could not run” reason, reduces confidence, and requests human review; it does not turn the missing-dependency condition into `BLOCK`.

**Evidence:** [`tools/sandbox_client.py`](../src/mergeguard/tools/sandbox_client.py), [`sandbox/jobs.py`](../src/mergeguard/sandbox/jobs.py), [`docker-compose.yml`](../docker-compose.yml), [`test_sandbox_client.py`](../tests/tools/test_sandbox_client.py), and [`test_result_classification.py`](../tests/sandbox/test_result_classification.py).

## ADR-03: require human review for BLOCK and low-confidence outcomes

**Status:** Accepted

The graph pauses at a LangGraph interrupt when a verdict is `BLOCK` or confidence falls below the configured threshold. The API validates a human decision and queues a resume action; the worker resumes the graph and records the final decision.

**Consequences:**

- An override requires a non-empty reason.
- An authenticated review submission is accepted into the queue only while the job is awaiting review.
- A queued review decision is not itself proof that the worker has completed resuming the graph; completion is represented by the later job status.

**Evidence:** [`workflow/graph.py`](../src/mergeguard/workflow/graph.py), [`api/app.py`](../src/mergeguard/api/app.py), [`worker/main.py`](../src/mergeguard/worker/main.py), [`test_human_review_resume.py`](../tests/integration/test_human_review_resume.py), and [`test_human_approval_policy.py`](../tests/workflow/test_human_approval_policy.py).

## ADR-04: decouple webhook requests from review processing

**Status:** Accepted

The API queues review jobs in Redis. A worker consumes jobs and stores run status and results; the API exposes job status and operational metrics.

**Consequences:**

- Webhook requests return after enqueueing rather than waiting for the full review.
- Job state, verdicts, and human-review decisions are persisted by the database layer.
- Operational metrics are computed from stored tool events and runs; no savings or success-rate value is claimed without measured data.

**Evidence:** [`api/app.py`](../src/mergeguard/api/app.py), [`worker/main.py`](../src/mergeguard/worker/main.py), [`storage/db.py`](../src/mergeguard/storage/db.py), [`observability/metrics.py`](../src/mergeguard/observability/metrics.py), and [`test_worker_sandbox_flow.py`](../tests/integration/test_worker_sandbox_flow.py).

## ADR-05: report measured evidence separately from design claims

**Status:** Accepted

Documentation distinguishes automated test results, golden PR evaluation results, operational metrics, and deployment status. They are separate kinds of evidence and must not be substituted for one another.

**Consequences:**

- The local test-suite result is reported as `115 passed in 54.93s`, copied from the latest test command output.
- Golden PR accuracy remains unreported until human-labeled examples have been evaluated and a result file exists.
- Operational values remain unreported until read from `/metrics`.
- MergeGuard is not described as deployed to Cloud Run.

**Evidence:** [`README.md`](../README.md), [`evaluation/scoring.py`](../src/mergeguard/evaluation/scoring.py), [`eval/golden_prs.json`](../eval/golden_prs.json), and [`api/app.py`](../src/mergeguard/api/app.py).

## ADR-06: missing sandbox dependencies are non-blocking errors

**Status:** Accepted

When pytest cannot run because imports or dependencies are missing in the network-disabled sandbox, the runner returns status `error`. This is different from a test assertion failure: the verdict logic does not automatically block on the inability to run tests, but lowers confidence and requires human review.

**Evidence:** [`sandbox/jobs.py`](../src/mergeguard/sandbox/jobs.py), [`workflow/graph.py`](../src/mergeguard/workflow/graph.py), and [`test_result_classification.py`](../tests/sandbox/test_result_classification.py).
