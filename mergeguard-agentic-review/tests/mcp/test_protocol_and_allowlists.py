from __future__ import annotations

import asyncio

from mcp.shared.memory import create_connected_server_and_client_session

from mergeguard.agents.mcp_client import (
    AGENT_TOOL_ALLOWLISTS,
    MCP_SERVER_TOOL_ALLOWLISTS,
    call_agent_tool,
    list_agent_tools,
    tool_is_allowed,
)
from mergeguard.mcp_servers import github_server, security_server, test_runner_server


async def _list_tools(server):
    async with create_connected_server_and_client_session(server) as session:
        return await session.list_tools()


def test_each_fastmcp_server_lists_tools_over_mcp_protocol():
    github_tools = asyncio.run(_list_tools(github_server.mcp)).tools
    test_tools = asyncio.run(_list_tools(test_runner_server.mcp)).tools
    security_tools = asyncio.run(_list_tools(security_server.mcp)).tools

    assert {tool.name for tool in github_tools} == {
        "get_pull_request",
        "get_changed_files",
        "get_file_content",
        "get_pr_conversation",
    }
    assert {tool.name for tool in test_tools} == {"run_tests"}
    assert {tool.name for tool in security_tools} == {"scan_dependencies"}


def test_code_analysis_allowlist_excludes_test_execution():
    assert "test_runner.run_tests" not in AGENT_TOOL_ALLOWLISTS["code_analysis"]
    assert tool_is_allowed("code_analysis", "github", "get_file_content") is True
    assert tool_is_allowed("code_analysis", "test_runner", "run_tests") is False
    assert tool_is_allowed("security_review", "github", "get_file_content") is True
    assert tool_is_allowed("security_review", "security", "scan_dependencies") is True
    assert tool_is_allowed("security_review", "test_runner", "run_tests") is False
    assert tool_is_allowed("test_execution", "test_runner", "run_tests") is True
    assert tool_is_allowed("test_execution", "github", "get_pull_request") is False


def test_agent_tool_discovery_runs_over_stdio_with_allowlists():
    code_tools = list_agent_tools("code_analysis")
    test_tools = list_agent_tools("test_execution")
    security_tools = list_agent_tools("security_review")

    assert code_tools == {
        "github.get_pull_request",
        "github.get_changed_files",
        "github.get_file_content",
        "github.get_pr_conversation",
    }
    assert test_tools == {"test_runner.run_tests"}
    assert "test_runner.run_tests" not in code_tools
    assert "security.scan_dependencies" in security_tools
    assert "github.get_file_content" in security_tools


def test_agent_tool_discovery_starts_only_allowed_servers(monkeypatch):
    started_servers = []

    async def list_tools(server):
        started_servers.append(server)
        return MCP_SERVER_TOOL_ALLOWLISTS[server]

    monkeypatch.setattr("mergeguard.agents.mcp_client._list_server_tools", list_tools)

    assert list_agent_tools("code_analysis") == AGENT_TOOL_ALLOWLISTS["code_analysis"]
    assert started_servers == ["github"]

    started_servers.clear()
    assert list_agent_tools("test_execution") == {"test_runner.run_tests"}
    assert started_servers == ["test_runner"]

    started_servers.clear()
    assert list_agent_tools("security_review") == AGENT_TOOL_ALLOWLISTS["security_review"]
    assert started_servers == ["github", "security"]


def test_disallowed_tool_fails_before_starting_a_server(monkeypatch):
    def unexpected_call(*args, **kwargs):
        raise AssertionError(f"a disallowed MCP server must not start: {args}, {kwargs}")

    monkeypatch.setattr("mergeguard.agents.mcp_client.asyncio.run", unexpected_call)

    try:
        call_agent_tool("code_analysis", "test_runner", "run_tests", {"job_id": "job"})
    except PermissionError as error:
        assert "not allowed" in str(error)
    else:
        raise AssertionError("tool allowlist was not enforced")


def test_tool_schemas_do_not_accept_arbitrary_commands_or_paths():
    github_tools = {tool.name: tool for tool in asyncio.run(_list_tools(github_server.mcp)).tools}
    test_tools = {tool.name: tool for tool in asyncio.run(_list_tools(test_runner_server.mcp)).tools}
    security_tools = {tool.name: tool for tool in asyncio.run(_list_tools(security_server.mcp)).tools}

    test_properties = test_tools["run_tests"].inputSchema["properties"]
    assert set(test_properties) == {"job_id"}
    assert "command" not in test_properties
    assert "command" not in security_tools["scan_dependencies"].inputSchema["properties"]
    assert set(github_tools["get_file_content"].inputSchema["properties"]) == {
        "owner",
        "repo",
        "path",
        "ref",
    }