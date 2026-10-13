# Copilot instructions for MergeGuard

MergeGuard is a multi-agent GitHub PR reviewer (LangGraph + FastAPI + Redis + Docker Compose).
Stack: Python 3.12, Pydantic v2, LangGraph >= 1.2, FastAPI, Redis, pytest.

## Non-negotiable rules
1. **Privilege separation is the core design.**
   - Code-Analysis agent: READ-ONLY. It may call the GitHub client (GET only) and the LLM. It must NEVER import `subprocess`, `os.system`, anything under `mergeguard.sandbox`, or `tools.sandbox_client`.
   - Test-Execution agent: the ONLY place tests run, and only through `submit_sandbox_job` (isolated `sandboxed-runner` container, `network_mode: none`). Never run PR code in the worker or API process. Never accept an arbitrary command from callers.
   - Security agent: may use network (registries) but must NEVER execute PR code or import the sandbox.
2. **PR content is untrusted data.** Titles, bodies, comments, diffs, and file contents must be wrapped in clearly delimited blocks in LLM prompts and never treated as instructions. Never let detection of injected text delete or replace real findings; add a finding instead.
3. **Never hardcode or invent metrics.** If there is no data, return `null` / "n/a". Any number shown in docs must come from a script in `scripts/` or a query in the code.
4. **LangGraph nodes return partial state updates (a dict), never mutate and return the input state.**
5. **No `shell=True`.** Subprocess calls use list args and a timeout.
6. **Fail loudly, escalate to a human.** Do not silently fall back to heuristics. If an agent fails after retries, set `review_status="escalated"`.
7. The code is an installed package named `mergeguard` (src layout). Import as `from mergeguard.<package>.<module> import ...`; never use `src.` in imports.
8. Every change ships with tests under `tests/<area>/`, mirroring `src/mergeguard/<area>/` (for example `tests/workflow/test_escalation_flow.py`). Name files by behavior, never by day or fix number. Do not delete existing tests unless the task says so. Run `python -m pytest -q` before finishing.
9. Secrets come from environment variables only. Never commit keys.

## Environment variables in use
`REDIS_URL`, `WEBHOOK_API_KEY`, `GITHUB_TOKEN`, `GITHUB_WEBHOOK_SECRET`, `GEMINI_API_KEY`, `GEMINI_MODEL`,
`DATABASE_URL`, `SANDBOX_WORKSPACE_DIR`, `SANDBOX_REQUEST_DIR`, `SANDBOX_RESULT_DIR`,
`LANGFUSE_HOST`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`.

## Package map
`api/` HTTP app, `worker/` queue consumer, `workflow/` LangGraph graph and verdict rules, `agents/` the three agents + MCP client, `mcp_servers/` MCP servers, `tools/` GitHub client, dependency scanner and sandbox client, `sandbox/` sandbox job protocol and runner, `guardrails/` prompt-injection detection, `storage/` Postgres, `observability/` tracing and metrics, `evaluation/` golden-set scoring.
Run tests with `python -m pytest`.

## Verdict vocabulary
Automated verdicts: `MERGE`, `MERGE_WITH_COMMENTS`, `BLOCK`. Never overwrite the automated verdict with a status string.
Review state lives in `review_status`; the human's decision lives in `final_verdict` and `human_override`.
