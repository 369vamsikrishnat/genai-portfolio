from __future__ import annotations

import asyncio
import json
import os
import sys
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER_MODULES = {
    "github": "mergeguard.mcp_servers.github_server",
    "test_runner": "mergeguard.mcp_servers.test_runner_server",
    "security": "mergeguard.mcp_servers.security_server",
}
SERVER_ENV_ALLOWLIST = {
    "github": {"GITHUB_TOKEN", "DATABASE_URL", "LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_HOST"},
    "test_runner": {"SANDBOX_WORKSPACE_DIR", "SANDBOX_REQUEST_DIR", "SANDBOX_RESULT_DIR", "DATABASE_URL", "LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_HOST"},
    "security": {"DATABASE_URL", "GEMINI_API_KEY", "GEMINI_MODEL", "GEMINI_MIN_REQUEST_INTERVAL_SECONDS", "LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_HOST"},
}
BASE_SERVER_ENV = {"PATH", "PYTHONPATH", "HOME", "LANG", "LC_ALL", "TMPDIR"}
MCP_SERVER_TOOL_ALLOWLISTS = {
    "github": frozenset(
        {"get_pull_request", "get_changed_files", "get_file_content", "get_pr_conversation"}
    ),
    "test_runner": frozenset({"run_tests"}),
    "security": frozenset({"scan_dependencies"}),
}

AGENT_TOOL_ALLOWLISTS = {
    "code_analysis": frozenset(
        {
            "github.get_pull_request",
            "github.get_changed_files",
            "github.get_file_content",
            "github.get_pr_conversation",
        }
    ),
    "test_execution": frozenset({"test_runner.run_tests"}),
    "security_review": frozenset(
        {
            "github.get_pull_request",
            "github.get_changed_files",
            "github.get_file_content",
            "github.get_pr_conversation",
            "security.scan_dependencies",
        }
    ),
}


def build_server_env(server: str) -> dict[str, str]:
    allowed = BASE_SERVER_ENV | SERVER_ENV_ALLOWLIST.get(server, set())
    env: dict[str, str] = {}
    for key in sorted(allowed):
        value = os.environ.get(key)
        if value is not None:
            env[key] = value
    return env


def tool_is_allowed(agent: str, server: str, tool: str) -> bool:
    return (
        tool in MCP_SERVER_TOOL_ALLOWLISTS.get(server, frozenset())
        and f"{server}.{tool}" in AGENT_TOOL_ALLOWLISTS.get(agent, frozenset())
    )


async def _call_mcp_tool(server: str, tool: str, arguments: dict[str, Any]) -> Any:
    module = SERVER_MODULES[server]
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", module],
        env=build_server_env(server),
    )
    async with stdio_client(parameters) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.call_tool(tool, arguments=arguments)

    if result.isError:
        raise RuntimeError(f"MCP tool {server}.{tool} returned an error.")
    structured = getattr(result, "structuredContent", None)
    if structured is not None:
        if isinstance(structured, dict) and set(structured) == {"result"}:
            return structured["result"]
        return structured
    text_blocks = [getattr(item, "text", None) for item in result.content]
    text_blocks = [text for text in text_blocks if isinstance(text, str)]
    if not text_blocks:
        return None
    text = "\n".join(text_blocks)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def call_agent_tool(agent: str, server: str, tool: str, arguments: dict[str, Any]) -> Any:
    if server not in SERVER_MODULES:
        raise ValueError(f"Unknown MCP server: {server}")
    if not tool_is_allowed(agent, server, tool):
        raise PermissionError(f"Agent {agent!r} is not allowed to call {server}.{tool}.")
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(_call_mcp_tool(server, tool, arguments))
    raise RuntimeError("Synchronous MergeGuard agents cannot call MCP from a running event loop.")


async def _list_server_tools(server: str) -> set[str]:
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", SERVER_MODULES[server]],
        env=build_server_env(server),
    )
    async with stdio_client(parameters) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.list_tools()
            return {tool.name for tool in result.tools}


def list_agent_tools(agent: str) -> set[str]:
    if agent not in AGENT_TOOL_ALLOWLISTS:
        raise ValueError(f"Unknown agent: {agent}")

    async def list_allowed() -> set[str]:
        discovered: set[str] = set()
        for server in SERVER_MODULES:
            if not any(
                f"{server}.{tool}" in AGENT_TOOL_ALLOWLISTS[agent]
                for tool in MCP_SERVER_TOOL_ALLOWLISTS[server]
            ):
                continue
            server_tools = await _list_server_tools(server)
            discovered.update(
                f"{server}.{tool}"
                for tool in server_tools
                if tool_is_allowed(agent, server, tool)
            )
        return discovered

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(list_allowed())
    raise RuntimeError("Synchronous MergeGuard agents cannot list MCP tools from a running event loop.")


__all__ = [
    "AGENT_TOOL_ALLOWLISTS",
    "MCP_SERVER_TOOL_ALLOWLISTS",
    "SERVER_ENV_ALLOWLIST",
    "build_server_env",
    "call_agent_tool",
    "list_agent_tools",
    "tool_is_allowed",
]