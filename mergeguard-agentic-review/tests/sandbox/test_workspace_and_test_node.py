from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import pytest

from mergeguard.workflow.graph import build_graph, test_execution_node as run_test_execution_node
from mergeguard.sandbox.jobs import extract_source_archive
from mergeguard.tools.sandbox_client import SandboxedTestRunner, TestResult


def test_runner_delegates_to_isolated_job_runner(monkeypatch):
    expected = TestResult(status="passed", summary="Isolated tests passed.")
    calls = []

    def submit_sandbox_job(job_id: str) -> TestResult:
        calls.append(job_id)
        return expected

    monkeypatch.setattr("mergeguard.sandbox.jobs.submit_sandbox_job", submit_sandbox_job)
    runner = SandboxedTestRunner()
    job_id = "d9428888-122b-4c01-a4cf-2fca3fc3e45e"
    result = runner.run_tests(job_id=job_id)

    assert result is expected
    assert calls == [job_id]
    assert result.network_disabled is True
    assert result.coverage_delta is None


def test_graph_keeps_test_execution_node():
    graph = build_graph()
    assert "test_execution" in graph.nodes


def test_test_execution_node_preserves_precomputed_isolated_result(monkeypatch):
    expected = {"status": "passed", "summary": "PR tests passed."}
    state = {"test_results": [expected]}

    result = run_test_execution_node(state)

    assert result == {}
    assert state["test_results"] == [expected]


def test_source_archive_extracts_under_the_job_workspace(tmp_path: Path):
    archive = BytesIO()
    with ZipFile(archive, "w") as source:
        source.writestr("repo-head/pyproject.toml", "[project]\nname='sample'\n")
        source.writestr("repo-head/tests/test_sample.py", "def test_ok(): assert True\n")

    destination = tmp_path / "job"
    extract_source_archive(archive.getvalue(), destination)

    assert (destination / "pyproject.toml").is_file()
    assert (destination / "tests" / "test_sample.py").is_file()


def test_source_archive_rejects_parent_directory_paths(tmp_path: Path):
    archive = BytesIO()
    with ZipFile(archive, "w") as source:
        source.writestr("repo-head/../../outside.txt", "unsafe")

    with pytest.raises(ValueError, match="unsafe path"):
        extract_source_archive(archive.getvalue(), tmp_path / "job")

    assert not (tmp_path / "outside.txt").exists()
