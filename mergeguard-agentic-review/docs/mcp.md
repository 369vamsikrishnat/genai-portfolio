# MergeGuard MCP Servers

MergeGuard uses the official Python MCP SDK and stdio transport to expose three least-privilege servers:

- `github`: read-only pull request metadata, changed files, file contents, and conversation comments.
- `test_runner`: `run_tests(job_id)`, which delegates to the isolated sandbox runner.
- `security`: `scan_dependencies(dependency_files, job_id)`, which audits fetched manifest names and contents without installing packages.

Run a server from the project root:

```powershell
python -m mergeguard.mcp_servers.github_server
python -m mergeguard.mcp_servers.test_runner_server
python -m mergeguard.mcp_servers.security_server
```

The graph agents connect through MCP client sessions. `src/mergeguard/agents/mcp_client.py` enforces an allowlist before starting a server: Code Analysis can call only `github`; Test Execution can call only `test_runner`; Security can call `github` read tools and `security.scan_dependencies`. No tool accepts a shell command, and the test runner accepts only a `job_id`.

## What MCP standardizes

MCP standardizes tool discovery and invocation across clients and servers: initialization, `tools/list`, `tools/call`, typed input schemas, structured results, and transport lifecycle. A client can discover and call a tool without depending on the server's internal Python implementation.

A hand-written function-calling schema only describes a tool interface for one model or provider. It does not standardize client/server negotiation, discovery, transport, or invocation. MCP provides that protocol layer; MergeGuard still enforces authorization through per-agent allowlists and safe tool implementations.