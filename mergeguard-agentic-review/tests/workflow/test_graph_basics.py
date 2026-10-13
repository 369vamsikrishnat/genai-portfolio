from mergeguard.workflow.graph import build_graph
from mergeguard.tools.github_client import GitHubClient


def test_build_graph_has_expected_nodes():
    graph = build_graph()

    assert "code_analysis" in graph.nodes
    assert "test_execution" in graph.nodes
    assert "security_review" in graph.nodes
    assert "orchestrator" in graph.nodes


def test_github_client_fetches_pull_request(monkeypatch):
    class DummyResponse:
        def __init__(self, payload, status_code=200):
            self._payload = payload
            self.status_code = status_code

        def raise_for_status(self):
            if self.status_code >= 400:
                raise RuntimeError("bad response")

        def json(self):
            return self._payload

    def fake_get(url, headers=None, timeout=None, params=None):
        assert "repos/owner/repo/pulls/123" in url
        assert params is None
        return DummyResponse({
            "number": 123,
            "title": "Fix login bug",
            "state": "open",
            "head": {"sha": "abc123"},
            "base": {"sha": "def456"},
        })

    class DummyClient:
        def get(self, url, headers=None, timeout=None, params=None):
            assert headers["Authorization"] == "Bearer token"
            return fake_get(url, headers=headers, timeout=timeout, params=params)

    monkeypatch.setattr("mergeguard.tools.github_client.httpx.Client", lambda **kwargs: DummyClient())

    client = GitHubClient(token="token")
    pr = client.get_pull_request("owner", "repo", 123)

    assert pr["number"] == 123
    assert pr["title"] == "Fix login bug"
