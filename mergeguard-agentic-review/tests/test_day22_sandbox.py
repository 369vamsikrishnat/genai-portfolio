from src.mergeguard.graph import build_graph
from src.mergeguard.tools.sandbox import SandboxConfig, SandboxedTestRunner, TestResult


def test_sandbox_config_restricts_network_and_writes():
    config = SandboxConfig(
        network_disabled=True,
        read_only_mounts=["/repo"],
        scratch_dir="/tmp/mergeguard-scratch",
    )

    assert config.network_disabled is True
    assert "/repo" in config.read_only_mounts
    assert config.scratch_dir == "/tmp/mergeguard-scratch"


def test_runner_returns_structured_test_result():
    runner = SandboxedTestRunner()
    result = runner.run_tests(
        repo_path=".",
        command=["python", "-m", "pytest", "tests/test_day20_graph.py", "-q"],
    )

    assert isinstance(result, TestResult)
    assert result.status in {"passed", "failed"}
    assert result.summary
    assert result.coverage_delta is not None
    assert result.network_disabled is True


def test_graph_keeps_test_execution_node():
    graph = build_graph()
    assert "test_execution" in graph.nodes
