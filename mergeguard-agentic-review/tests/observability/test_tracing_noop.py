from __future__ import annotations


from mergeguard.observability import tracing
from mergeguard.agents import code_analysis, security, test_execution
from mergeguard.agents.common import RiskFinding
from mergeguard.tools.sandbox_client import TestResult


class FakeObservation:
    def __init__(self, name, as_type, model=None):
        self.name = name
        self.as_type = as_type
        self.model = model
        self.updates = []
        self.ended = False

    def update(self, **values):
        self.updates.append(values)

    def end(self):
        self.ended = True


class FakeTrace:
    def __init__(self, trace_id):
        self.trace_id = trace_id
        self.observations = []

    def span(self, *, name, **kwargs):
        observation = FakeObservation(name, "span")
        self.observations.append(observation)
        return observation

    def generation(self, *, name, model=None, **kwargs):
        observation = FakeObservation(name, "generation", model)
        self.observations.append(observation)
        return observation

    def update(self, **kwargs):
        pass


class FakeLangfuse:
    def __init__(self):
        self.traces = {}
        self.flush_count = 0

    def trace(self, *, id, **kwargs):
        self.traces.setdefault(id, FakeTrace(id))
        return self.traces[id]

    def flush(self):
        self.flush_count += 1


def test_missing_langfuse_keys_make_all_helpers_noop(monkeypatch):
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
    monkeypatch.setattr(tracing, "_langfuse_client", None)
    monkeypatch.setattr(tracing, "_get_langfuse_client", lambda: None)
    monkeypatch.setattr(tracing.db, "record_tool_event", lambda job_id, tool, fn: fn())

    tracing.start_job_trace("job-1")
    with tracing.trace_observation("job-1", "code_analysis") as observation:
        assert observation is None
    assert tracing.record_tool_call("job-1", "github.get_pull_request", lambda: "ok") == "ok"
    tracing.finish_job_trace("job-1", status="completed", verdict="MERGE")


def test_agent_tool_and_generation_observation_names_use_job_trace(monkeypatch):
    client = FakeLangfuse()
    job_id = "dcae68ad-714e-4d03-84a3-85a0ddb5cd67"
    monkeypatch.setenv("GEMINI_API_KEY", "test-secret-value")
    monkeypatch.setattr(tracing, "_get_langfuse_client", lambda: client)
    monkeypatch.setattr(
        code_analysis,
        "_code_analysis_node",
        lambda state: {"code_findings": [RiskFinding(description="safe")], "injection_flags": []},
    )
    monkeypatch.setattr(
        security,
        "_security_review_node",
        lambda state: {"security_findings": [], "reasons": []},
    )
    monkeypatch.setattr(
        test_execution,
        "call_agent_tool",
        lambda agent, server, tool, arguments: TestResult(
            status="passed",
            summary="ok",
        ).model_dump(),
    )
    monkeypatch.setattr(tracing.db, "record_tool_event", lambda job_id, tool, fn: fn())

    tracing.start_job_trace(job_id)
    code_analysis.code_analysis_node({"job_id": job_id})
    security.security_review_node({"job_id": job_id})
    test_execution.test_execution_node({"job_id": job_id})
    with tracing.trace_observation(
        job_id,
        "gemini.code_analysis",
        generation=True,
        model="gemini-3.8-flash",
    ) as generation:
        tracing.update_observation(
            generation,
            output=[{"severity": "low", "description": "validated test-secret-value api_key=another-secret-value", "line_reference": "unknown"}],
            usage_details={"input": 12, "output": 4, "total": 16},
        )
    tracing.finish_job_trace(job_id, status="completed", verdict="MERGE")

    trace = client.traces[job_id]
    assert trace.trace_id == job_id
    assert {observation.name for observation in trace.observations} >= {
        "code_analysis",
        "test_execution",
        "security_review",
        "sandbox.run_tests",
        "gemini.code_analysis",
    }
    generation_observation = next(
        observation for observation in trace.observations if observation.as_type == "generation"
    )
    assert generation_observation.model == "gemini-3.8-flash"
    assert generation_observation.updates[0]["usage_details"] == {"input": 12, "output": 4, "total": 16}
    assert generation_observation.updates[0]["output"][0]["description"] == "validated [REDACTED] [REDACTED]"
    assert generation_observation.ended is True