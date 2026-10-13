from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from mergeguard.tools.github_client import GitHubClient

mcp = FastMCP("mergeguard-github")


@mcp.tool()
def get_pull_request(owner: str, repo: str, pull_number: int) -> dict[str, Any]:
    """Read pull-request metadata from GitHub."""
    return GitHubClient().get_pull_request(owner, repo, pull_number)


@mcp.tool()
def get_changed_files(owner: str, repo: str, pull_number: int) -> list[dict[str, Any]]:
    """Read changed-file metadata for a pull request."""
    return GitHubClient().get_changed_files(owner, repo, pull_number)


@mcp.tool()
def get_file_content(owner: str, repo: str, path: str, ref: str) -> str | None:
    """Read one file's text content at a Git reference."""
    return GitHubClient().get_file_content(owner, repo, path, ref)


@mcp.tool()
def get_pr_conversation(owner: str, repo: str, pull_number: int) -> list[dict[str, Any]]:
    """Read issue and review comments for a pull request."""
    return GitHubClient().get_pr_conversation(owner, repo, pull_number)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()