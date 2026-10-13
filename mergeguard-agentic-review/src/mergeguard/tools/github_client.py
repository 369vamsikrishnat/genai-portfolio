from __future__ import annotations

import os
from typing import Any
from urllib.parse import quote

import httpx


class GitHubClient:
    PAGE_SIZE = 100
    MAX_CHANGED_FILES = 300
    MAX_FILE_CONTENT_BYTES = 200 * 1024

    def __init__(
        self,
        token: str | None = None,
        base_url: str = "https://api.github.com",
        client: httpx.Client | None = None,
    ):
        self.token = token or os.getenv("GITHUB_TOKEN")
        self.base_url = base_url.rstrip("/")
        self.client = client or httpx.Client(timeout=httpx.Timeout(30.0))
        self.headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            self.headers["Authorization"] = f"Bearer {self.token}"

    def get_pull_request(self, owner: str, repo: str, pull_number: int) -> dict[str, Any]:
        url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pull_number}"
        response = self.client.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def get_changed_files(self, owner: str, repo: str, pull_number: int) -> list[dict[str, Any]]:
        files, _ = self.get_changed_files_paged(owner, repo, pull_number)
        return files

    def get_changed_files_paged(
        self, owner: str, repo: str, pull_number: int
    ) -> tuple[list[dict[str, Any]], bool]:
        url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pull_number}/files"
        return self._get_paginated(url, max_items=self.MAX_CHANGED_FILES)

    def get_file_content(self, owner: str, repo: str, path: str, ref: str) -> str | None:
        safe_path = quote(path, safe="/")
        url = f"{self.base_url}/repos/{owner}/{repo}/contents/{safe_path}"
        content = bytearray()
        with self.client.stream(
            "GET",
            url,
            headers={**self.headers, "Accept": "application/vnd.github.raw+json"},
            params={"ref": ref},
        ) as response:
            if response.status_code == 404:
                return None
            response.raise_for_status()
            for chunk in response.iter_bytes():
                remaining = self.MAX_FILE_CONTENT_BYTES - len(content)
                content.extend(chunk[:remaining])
                if len(content) >= self.MAX_FILE_CONTENT_BYTES:
                    break
            encoding = response.encoding or "utf-8"
        return bytes(content).decode(encoding, errors="replace")

    def get_pr_conversation(self, owner: str, repo: str, pull_number: int) -> list[dict[str, Any]]:
        comments: list[dict[str, Any]] = []
        for endpoint in ("issues", "pulls"):
            url = f"{self.base_url}/repos/{owner}/{repo}/{endpoint}/{pull_number}/comments"
            page_comments, _ = self._get_paginated(url)
            comments.extend(page_comments)
        return comments

    def _get_paginated(
        self,
        url: str,
        *,
        max_items: int | None = None,
    ) -> tuple[list[dict[str, Any]], bool]:
        items: list[dict[str, Any]] = []
        page = 1
        truncated = False

        while True:
            response = self.client.get(
                url,
                headers=self.headers,
                params={"per_page": self.PAGE_SIZE, "page": page},
            )
            response.raise_for_status()
            page_items = response.json()
            remaining = max_items - len(items) if max_items is not None else len(page_items)
            items.extend(page_items[:remaining])

            if max_items is not None and len(items) >= max_items:
                truncated = "next" in response.links
                break
            if len(page_items) < self.PAGE_SIZE:
                break
            page += 1

        return items, truncated

    def get_source_archive(self, owner: str, repo: str, ref: str) -> bytes:
        url = f"{self.base_url}/repos/{owner}/{repo}/zipball/{ref}"
        archive = bytearray()
        with self.client.stream(
            "GET",
            url,
            headers=self.headers,
            timeout=httpx.Timeout(60.0),
            follow_redirects=True,
        ) as response:
            response.raise_for_status()
            for chunk in response.iter_bytes():
                archive.extend(chunk)
                if len(archive) > 50 * 1024 * 1024:
                    raise ValueError("GitHub source archive exceeds the 50 MiB limit.")
        return bytes(archive)
