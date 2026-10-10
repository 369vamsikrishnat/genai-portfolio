from src.mergeguard.graph import RiskFinding, analyze_code_risk, build_graph


def test_risk_finding_model_validates_required_fields():
    finding = RiskFinding(
        severity="high",
        description="Possible null dereference in auth flow",
        line_reference="src/auth.py:42",
    )

    assert finding.severity == "high"
    assert finding.line_reference == "src/auth.py:42"


def test_analyze_code_risk_returns_structured_findings():
    diff = """
    --- a/src/auth.py
    +++ b/src/auth.py
    @@
    - def get_user(token):
    -     return session.get(token)
    + def get_user(token):
    +     if not token:
    +         return None
    +     return session.get(token)
    """
    context = "The auth utility returns a user from the session. A missing token could bypass validation if callers assume a valid object."

    findings = analyze_code_risk(diff, context)

    assert len(findings) >= 1
    assert findings[0].severity in {"low", "medium", "high"}
    assert "token" in findings[0].description.lower()
    assert findings[0].line_reference


def test_graph_contains_code_analysis_node():
    graph = build_graph()
    assert "code_analysis" in graph.nodes
