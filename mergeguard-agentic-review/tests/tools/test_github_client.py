from __future__ import annotations

import httpx

from mergeguard.tools.github_client import GitHubClient


def _client(handler):
    transport = httpx.MockTransport(handler)
    http_client = httpx.Client(transport=transport, timeout=httpx.Timeout(30.0))
    return GitHubClient(token="test-token", client=http_client)


def test_changed_files_fetches_all_pages_and_preserves_list_return_shape():
    methods = []
    requested_pages = []

    def handler(request):
        methods.append(request.method)
        requested_pages.append(int(request.url.params["page"]))
        page = int(request.url.params["page"])
        start = (page - 1) * 100
        end = min(start + 100, 120)
        return httpx.Response(200, json=[{"filename": f"file-{i}.py"} for i in range(start, end)])

    client = _client(handler)
    files = client.get_changed_files("owner", "repo", 123)

    assert len(files) == 120
    assert requested_pages == [1, 2]
    assert methods == ["GET", "GET"]


def test_changed_files_reports_truncation_at_three_hundred_file_cap():
    requested_pages = []

    def handler(request):
        page = int(request.url.params["page"])
        requested_pages.append(page)
        headers = {"Link": '<https://api.github.com/next>; rel="next"'} if page < 4 else {}
        return httpx.Response(200, json=[{"filename": f"file-{page}-{i}.py"} for i in range(100)], headers=headers)

    files, truncated = _client(handler).get_changed_files_paged("owner", "repo", 123)

    assert len(files) == 300
    assert truncated is True
    assert requested_pages == [1, 2, 3]


def test_file_content_returns_none_for_missing_file_and_caps_response_size():
    methods = []

    def handler(request):
        methods.append(request.method)
        assert request.headers["accept"] == "application/vnd.github.raw+json"
        assert request.url.params["ref"] == "main"
        if request.url.path.endswith("missing.py"):
            return httpx.Response(404)
        return httpx.Response(200, content=b"a" * (200 * 1024 + 20))

    client = _client(handler)

    assert client.get_file_content("owner", "repo", "missing.py", "main") is None
    content = client.get_file_content("owner", "repo", "src/app.py", "main")

    assert content is not None
    assert len(content.encode("utf-8")) == 200 * 1024
    assert methods == ["GET", "GET"]


def test_pr_conversation_paginates_both_comment_endpoints_and_uses_get_only():
    methods = []
    requested_endpoints = []

    def handler(request):
        methods.append(request.method)
        requested_endpoints.append(request.url.path)
        page = int(request.url.params["page"])
        if "/issues/123/comments" in request.url.path:
            comments = [{"id": index} for index in range(100)] if page == 1 else [{"id": 100}]
        else:
            comments = [{"id": 200}]
        return httpx.Response(200, json=comments)

    comments = _client(handler).get_pr_conversation("owner", "repo", 123)

    assert len(comments) == 102
    assert any("/issues/123/comments" in endpoint for endpoint in requested_endpoints)
    assert any("/pulls/123/comments" in endpoint for endpoint in requested_endpoints)
    assert methods and set(methods) == {"GET"}