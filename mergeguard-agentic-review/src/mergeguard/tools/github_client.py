from __future__ import annotations

import os
from typing import Any

import httpx


class GitHubClient:
    def __init__(self, token: str | None = None, base_url: str = "https://api.github.com"):
        self.token = token or os.getenv("GITHUB_TOKEN")
        self.base_url = base_url.rstrip("/")
        self.headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            self.headers["Authorization"] = f"Bearer {self.token}"

    def get_pull_request(self, owner: str, repo: str, pull_number: int) -> dict[str, Any]:
        url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pull_number}"
        response = httpx.get(url, headers=self.headers, timeout=30.0)
        response.raise_for_status()
        return response.json()

    def get_changed_files(self, owner: str, repo: str, pull_number: int) -> list[dict[str, Any]]:
        url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pull_number}/files"
        response = httpx.get(url, headers=self.headers, timeout=30.0)
        response.raise_for_status()
        return response.json()
