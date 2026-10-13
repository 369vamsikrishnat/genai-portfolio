from __future__ import annotations

import json
import subprocess

from mergeguard.workflow import graph
from mergeguard.agents import security
from mergeguard.agents.common import SecurityFinding
from mergeguard.tools import dependency_scanner


PIP_AUDIT_JSON = {
    "dependencies": [
        {
            "name": "demo-package",
            "version": "1.2.3",
            "vulns": [
                {
                    "id": "PYSEC-2025-10",
                    "aliases": ["CVE-2025-12345", "GHSA-abcd-1234-efgh"],
                    "description": "A remotely exploitable vulnerability.",
                    "fix_versions": ["1.2.4"],
                }
            ],
        }
    ]
}

NPM_AUDIT_JSON = {
    "vulnerabilities": {
        "info-package": {"severity": "info", "via": []},
        "low-package": {"severity": "low", "via": []},
        "moderate-package": {"severity": "moderate", "via": []},
        "high-package": {"severity": "high", "via": []},
        "critical-package": {"severity": "critical", "via": []},
    }
}


class FakeGitHubClient:
    def __init__(self, contents):
        self.contents = contents
        self.requests = []

    def get_file_content(self, owner, repo, path, ref):
        self.requests.append((owner, repo, path, ref))
        return self.contents.get(path)


def _state(changed_files):
    return {
        "job_id": "dcae68ad-714e-4d03-84a3-85a0ddb5cd67",
        "owner": "acme",
        "repo": "widget",
        "head_sha": "head-123",
        "changed_files": changed_files,
    }


def _mock_security_mcp(monkeypatch, github):
    def call_agent_tool(agent, server, tool, arguments):
        if server == "github" and tool == "get_file_content":
            return github.get_file_content(
                arguments["owner"],
                arguments["repo"],
                arguments["path"],
                arguments["ref"],
            )
        if server == "security" and tool == "scan_dependencies":
            return dependency_scanner.scan_dependency_files(
                arguments["dependency_files"],
                arguments["job_id"],
            )
        raise AssertionError(f"Unexpected MCP call: {agent}.{server}.{tool}")

    monkeypatch.setattr(security, "call_agent_tool", call_agent_tool)


def test_pip_audit_vulnerability_is_triaged_and_keeps_advisory_ids(monkeypatch):
    github = FakeGitHubClient({"requirements.txt": "demo-package==1.2.3\n"})
    commands = []

    class FakeModels:
        def generate_content(self, *, model, contents, config):
            assert "CVE-2025-12345" in contents
            assert config.response_schema is SecurityFinding
            return type(
                "Response",
                (),
                {"parsed": {"severity": "critical", "description": "Remote code execution is practical.", "package_name": "demo-package"}},
            )()

    class FakeGeminiClient:
        def __init__(self, *, api_key):
            assert api_key == "test-key"
            self.models = FakeModels()

    def fake_run(command, **kwargs):
        commands.append((command, kwargs))
        return subprocess.CompletedProcess(command, 1, json.dumps(PIP_AUDIT_JSON), "")

    _mock_security_mcp(monkeypatch, github)
    monkeypatch.setattr(dependency_scanner.genai, "Client", FakeGeminiClient)
    monkeypatch.setattr(dependency_scanner.subprocess, "run", fake_run)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-3.8-flash")

    result = security.security_review_node(_state(["requirements.txt"]))

    assert github.requests == [("acme", "widget", "requirements.txt", "head-123")]
    command, options = commands[0]
    assert command[0] == "pip-audit"
    assert command[1:2] == ["-r"]
    assert command[3:] == ["--no-deps", "--disable-pip", "--format", "json"]
    assert options["timeout"] == 120
    assert options["shell"] is False
    finding = result["security_findings"][0]
    assert finding.severity == "critical"
    assert "CVE-2025-12345" in finding.description
    assert "GHSA-abcd-1234-efgh" in finding.description
    assert graph.combine_verdict(security_findings=[finding.model_dump()])["verdict"] == "BLOCK"


def test_pip_audit_unpinned_requirements_report_low_finding_and_reason(monkeypatch):
    github = FakeGitHubClient({"requirements-dev.txt": "demo-package>=1.2\n"})

    def fake_run(command, **kwargs):
        return subprocess.CompletedProcess(command, 2, "", "requirements are not pinned")

    _mock_security_mcp(monkeypatch, github)
    monkeypatch.setattr(dependency_scanner.subprocess, "run", fake_run)

    result = security.security_review_node(_state(["requirements-dev.txt"]))

    assert result["security_findings"] == [
        SecurityFinding(
            severity="low",
            description="dependency scan could not run: requirements are not pinned",
            package_name="unknown",
        )
    ]
    assert result["reasons"] == ["dependency scan could not run: requirements are not pinned"]


def test_pip_vulnerability_triage_clamps_low_to_medium(monkeypatch):
    class FakeModels:
        def generate_content(self, **kwargs):
            return type(
                "Response",
                (),
                {"parsed": {"severity": "low", "description": "Limited impact.", "package_name": "demo-package"}},
            )()

    class FakeGeminiClient:
        def __init__(self, *, api_key):
            self.models = FakeModels()

    monkeypatch.setattr(dependency_scanner.genai, "Client", FakeGeminiClient)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-3.8-flash")

    finding = dependency_scanner._triage_vulnerability(
        {"package_name": "demo-package", "id": "PYSEC-2025-10", "aliases": ["CVE-2025-12345"]},
        "dcae68ad-714e-4d03-84a3-85a0ddb5cd67",
    )

    assert finding.severity == "medium"
    assert "CVE-2025-12345" in finding.description


def test_npm_audit_maps_all_supported_severities(monkeypatch):
    github = FakeGitHubClient(
        {
            "web/package.json": '{"name":"web"}',
            "web/package-lock.json": '{"name":"web","lockfileVersion":3}',
        }
    )
    commands = []

    def fake_run(command, **kwargs):
        commands.append((command, kwargs))
        return subprocess.CompletedProcess(command, 1, json.dumps(NPM_AUDIT_JSON), "")

    _mock_security_mcp(monkeypatch, github)
    monkeypatch.setattr(dependency_scanner.shutil, "which", lambda binary: "C:/node/npm.cmd")
    monkeypatch.setattr(dependency_scanner.subprocess, "run", fake_run)

    result = security.security_review_node(
        _state(["web/package.json", "web/package-lock.json"])
    )

    severities = {finding.package_name: finding.severity for finding in result["security_findings"]}
    assert severities == {
        "info-package": "low",
        "low-package": "low",
        "moderate-package": "medium",
        "high-package": "high",
        "critical-package": "critical",
    }
    command, options = commands[0]
    assert command[1:] == ["audit", "--package-lock-only", "--json"]
    assert options["timeout"] == 120
    assert options["shell"] is False
    assert options["cwd"].name == "0"


def test_missing_npm_records_skip_reason(monkeypatch):
    github = FakeGitHubClient({"package-lock.json": '{"lockfileVersion":3}'})
    _mock_security_mcp(monkeypatch, github)
    monkeypatch.setattr(dependency_scanner.shutil, "which", lambda binary: None)

    result = security.security_review_node(_state(["package-lock.json"]))

    assert result["security_findings"] == []
    assert result["reasons"] == ["npm audit skipped: npm is not installed"]


def test_security_skip_makes_no_github_or_subprocess_calls(monkeypatch):
    def unexpected_call(*args, **kwargs):
        raise AssertionError("security scan must be skipped")

    monkeypatch.setattr(security, "call_agent_tool", unexpected_call)
    monkeypatch.setattr(dependency_scanner.subprocess, "run", unexpected_call)

    result = security.security_review_node(_state(["src/app.py"]))

    assert result == {"security_findings": [], "agents_skipped": ["security_review"]}


def test_dependency_scan_reason_survives_parallel_graph_verdict(monkeypatch):
    github = FakeGitHubClient({"requirements-dev.txt": "demo-package>=1.2\n"})

    def fake_run(command, **kwargs):
        return subprocess.CompletedProcess(command, 2, "", "requirements are not pinned")

    _mock_security_mcp(monkeypatch, github)
    monkeypatch.setattr(dependency_scanner.subprocess, "run", fake_run)
    monkeypatch.setattr(graph, "code_analysis_node", lambda state: {"code_findings": []})
    monkeypatch.setattr(
        graph,
        "test_execution_node",
        lambda state: {"test_results": [{"status": "passed", "summary": "ok"}]},
    )

    result = graph.build_graph().compile().invoke(
        {
            **_state(["requirements-dev.txt"]),
            "pr_diff": "",
        },
        config={"recursion_limit": graph.GRAPH_RECURSION_LIMIT},
    )

    assert "dependency scan could not run: requirements are not pinned" in result["reasons"]
    assert "tests passed" in result["reasons"]