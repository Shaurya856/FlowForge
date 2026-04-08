"""
Test Suite for Scenario-Based API Workflow Execution and Load Simulation Platform
BCSE301P - Software Engineering Lab
Author: Shaurya Maloo (23BAI0185)
"""

import pytest
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from sqlmodel import SQLModel, Session, create_engine
from db import (
    Workflow, WorkflowStep, Execution, ExecutionTrace, MockApiConfig
)
from modules.workflow_manager import (
    create_workflow, get_workflow, list_workflows, delete_workflow,
    add_step, get_steps, delete_step, validate_workflow, update_workflow
)
from modules.mock_api import get_mock_response, create_mock_config
from modules.anomaly_detector import detect_anomalies, zscore_anomalies, iqr_anomalies

# ─── Test DB setup ─────────────────────────────────────────────────────────────

TEST_DB_URL = "sqlite:///./test_platform.db"

@pytest.fixture(scope="session")
def test_engine():
    engine = create_engine(TEST_DB_URL)
    SQLModel.metadata.create_all(engine)
    yield engine
    SQLModel.metadata.drop_all(engine)
    import os
    if os.path.exists("./test_platform.db"):
        os.remove("./test_platform.db")

@pytest.fixture
def session(test_engine):
    with Session(test_engine) as s:
        yield s


# ═══════════════════════════════════════════════════════════════════════════════
# TC_01 — Workflow Creation
# ═══════════════════════════════════════════════════════════════════════════════

class TestWorkflowCreation:

    def test_create_workflow_basic(self, session):
        """TC_01: Verify a workflow can be created with name and description."""
        wf = create_workflow(session, "Login Flow", "Tests user authentication")
        assert wf.workflow_id is not None
        assert wf.name == "Login Flow"
        assert wf.description == "Tests user authentication"
        print(f"\n[TC_01] PASS — Workflow created: {wf.workflow_id}")

    def test_create_workflow_minimal(self, session):
        """TC_01b: Verify workflow creation with name only."""
        wf = create_workflow(session, "Minimal Workflow")
        assert wf.name == "Minimal Workflow"
        print(f"\n[TC_01b] PASS — Minimal workflow created")

    def test_get_workflow_by_id(self, session):
        """TC_01c: Verify workflow retrieval by ID."""
        wf = create_workflow(session, "Retrievable Workflow")
        fetched = get_workflow(session, wf.workflow_id)
        assert fetched is not None
        assert fetched.workflow_id == wf.workflow_id
        print(f"\n[TC_01c] PASS — Workflow retrieved successfully")

    def test_list_workflows(self, session):
        """TC_01d: Verify workflow listing returns all workflows."""
        create_workflow(session, "List Test WF 1")
        create_workflow(session, "List Test WF 2")
        wfs = list_workflows(session)
        assert len(wfs) >= 2
        print(f"\n[TC_01d] PASS — Listed {len(wfs)} workflows")

    def test_update_workflow(self, session):
        """TC_01e: Verify workflow update."""
        wf = create_workflow(session, "Old Name")
        updated = update_workflow(session, wf.workflow_id, name="New Name")
        assert updated.name == "New Name"
        print(f"\n[TC_01e] PASS — Workflow updated")

    def test_delete_workflow(self, session):
        """TC_01f: Verify workflow deletion."""
        wf = create_workflow(session, "Delete Me")
        deleted = delete_workflow(session, wf.workflow_id)
        assert deleted is True
        fetched = get_workflow(session, wf.workflow_id)
        assert fetched is None
        print(f"\n[TC_01f] PASS — Workflow deleted")

    def test_get_nonexistent_workflow(self, session):
        """TC_01g: Verify None returned for missing workflow."""
        result = get_workflow(session, "nonexistent-id-000")
        assert result is None
        print(f"\n[TC_01g] PASS — Non-existent workflow returns None")


# ═══════════════════════════════════════════════════════════════════════════════
# TC_02 — Step Configuration
# ═══════════════════════════════════════════════════════════════════════════════

class TestStepConfiguration:

    def test_add_step_to_workflow(self, session):
        """TC_02: Verify a step can be added to a workflow."""
        wf = create_workflow(session, "Step Test WF")
        step = add_step(
            session, wf.workflow_id,
            name="Login Step",
            endpoint="http://localhost:8000/mock/login",
            http_method="POST",
            body={"username": "admin", "password": "secret"},
            execution_order=0
        )
        assert step.step_id is not None
        assert step.workflow_id == wf.workflow_id
        assert step.http_method == "POST"
        print(f"\n[TC_02] PASS — Step added: {step.step_id}")

    def test_step_ordering(self, session):
        """TC_02b: Verify steps are returned in execution order."""
        wf = create_workflow(session, "Ordering WF")
        add_step(session, wf.workflow_id, "Step C", "/c", "GET", execution_order=2)
        add_step(session, wf.workflow_id, "Step A", "/a", "GET", execution_order=0)
        add_step(session, wf.workflow_id, "Step B", "/b", "GET", execution_order=1)
        steps = get_steps(session, wf.workflow_id)
        orders = [s.execution_order for s in steps]
        assert orders == sorted(orders)
        print(f"\n[TC_02b] PASS — Steps returned in order: {orders}")

    def test_step_with_variable_extraction(self, session):
        """TC_02c: Verify step stores variable extraction config."""
        wf = create_workflow(session, "VarExtract WF")
        step = add_step(
            session, wf.workflow_id,
            name="Get Token",
            endpoint="/mock/login",
            http_method="POST",
            extract_vars={"auth_token": "token"},
            execution_order=0
        )
        import json
        ev = json.loads(step.extract_vars)
        assert ev.get("auth_token") == "token"
        print(f"\n[TC_02c] PASS — Variable extraction config stored")

    def test_delete_step(self, session):
        """TC_02d: Verify step deletion."""
        wf = create_workflow(session, "StepDelete WF")
        step = add_step(session, wf.workflow_id, "Temp Step", "/temp", "GET", execution_order=0)
        deleted = delete_step(session, step.step_id)
        assert deleted is True
        remaining = get_steps(session, wf.workflow_id)
        assert not any(s.step_id == step.step_id for s in remaining)
        print(f"\n[TC_02d] PASS — Step deleted")

    def test_http_method_normalization(self, session):
        """TC_02e: Verify HTTP method stored in uppercase."""
        wf = create_workflow(session, "Method WF")
        step = add_step(session, wf.workflow_id, "Lowercase Method", "/test", "get", execution_order=0)
        assert step.http_method == "GET"
        print(f"\n[TC_02e] PASS — HTTP method normalized to uppercase")


# ═══════════════════════════════════════════════════════════════════════════════
# TC_03 — Workflow Validation
# ═══════════════════════════════════════════════════════════════════════════════

class TestWorkflowValidation:

    def test_validate_empty_workflow_fails(self, session):
        """TC_03: Verify empty workflow fails validation."""
        wf = create_workflow(session, "Empty WF")
        result = validate_workflow(session, wf.workflow_id)
        assert result["valid"] is False
        assert len(result["errors"]) > 0
        print(f"\n[TC_03] PASS — Empty workflow rejected: {result['errors']}")

    def test_validate_complete_workflow_passes(self, session):
        """TC_03b: Verify complete workflow passes validation."""
        wf = create_workflow(session, "Complete WF")
        add_step(session, wf.workflow_id, "Step 1", "http://api.test/endpoint", "GET", execution_order=0)
        result = validate_workflow(session, wf.workflow_id)
        assert result["valid"] is True
        print(f"\n[TC_03b] PASS — Complete workflow validated")

    def test_validate_nonexistent_workflow(self, session):
        """TC_03c: Verify validation fails for missing workflow."""
        result = validate_workflow(session, "fake-id-xyz")
        assert result["valid"] is False
        print(f"\n[TC_03c] PASS — Non-existent workflow validation handled")


# ═══════════════════════════════════════════════════════════════════════════════
# TC_04 — Mock API
# ═══════════════════════════════════════════════════════════════════════════════

class TestMockAPI:

    def test_builtin_mock_health(self):
        """TC_04: Verify built-in mock /mock/health returns 200."""
        result = get_mock_response("/mock/health", "GET")
        assert result["status_code"] == 200
        assert "status" in result["body"]
        print(f"\n[TC_04] PASS — Mock health: {result['body']}")

    def test_builtin_mock_login(self):
        """TC_04b: Verify built-in mock /mock/login returns token."""
        result = get_mock_response("/mock/login", "POST")
        assert result["status_code"] == 200
        assert "token" in result["body"]
        print(f"\n[TC_04b] PASS — Mock login token: {result['body']['token']}")

    def test_mock_unknown_endpoint_returns_404(self):
        """TC_04c: Verify unknown endpoint returns 404."""
        result = get_mock_response("/nonexistent/path", "GET")
        assert result["status_code"] == 404
        print(f"\n[TC_04c] PASS — Unknown endpoint returns 404")

    def test_mock_latency_in_range(self):
        """TC_04d: Verify mock response has latency value."""
        result = get_mock_response("/mock/health", "GET")
        assert result["latency"] >= 0
        print(f"\n[TC_04d] PASS — Mock latency: {result['latency']}ms")

    def test_custom_mock_config(self, session):
        """TC_04e: Verify custom mock config works."""
        config = create_mock_config(
            session,
            endpoint="/test/custom",
            http_method="GET",
            response_template={"data": "custom_value"},
            latency_min=5,
            latency_max=10,
            error_rate=0.0,
            status_code=200
        )
        assert config.mock_id is not None
        result = get_mock_response("/test/custom", "GET")
        assert result["status_code"] == 200
        print(f"\n[TC_04e] PASS — Custom mock config: {result['body']}")

    def test_mock_full_url_normalization(self):
        """TC_04f: Verify mock handles full URLs by stripping host."""
        result = get_mock_response("http://localhost:8000/mock/health", "GET")
        assert result["status_code"] == 200
        print(f"\n[TC_04f] PASS — Full URL normalized in mock lookup")


# ═══════════════════════════════════════════════════════════════════════════════
# TC_05 — Anomaly Detection
# ═══════════════════════════════════════════════════════════════════════════════

class TestAnomalyDetection:

    def test_zscore_detects_spike(self):
        """TC_05: Verify Z-score detects outlier values."""
        values = [100, 102, 98, 101, 99, 103, 97, 500]  # 500 is spike
        flags = zscore_anomalies(values)
        assert flags[-1] is True  # 500 should be flagged
        print(f"\n[TC_05] PASS — Z-score detected spike at index {flags.index(True)}")

    def test_zscore_no_anomaly(self):
        """TC_05b: Verify Z-score passes normal data."""
        values = [100, 102, 98, 101, 99, 103, 97, 100]
        flags = zscore_anomalies(values)
        assert not any(flags)
        print(f"\n[TC_05b] PASS — No false positives on normal data")

    def test_iqr_detects_outlier(self):
        """TC_05c: Verify IQR method detects outlier."""
        values = [50, 55, 48, 52, 53, 51, 49, 200]  # 200 is outlier
        flags = iqr_anomalies(values)
        assert flags[-1] is True
        print(f"\n[TC_05c] PASS — IQR detected outlier")

    def test_anomaly_detection_insufficient_data(self):
        """TC_05d: Verify graceful handling with < 3 data points."""
        flags = zscore_anomalies([100, 200])
        assert flags == [False, False]
        print(f"\n[TC_05d] PASS — Insufficient data handled gracefully")

    def test_detect_anomalies_no_traces(self):
        """TC_05e: Verify anomaly detection handles missing execution."""
        result = detect_anomalies("nonexistent-exec-id")
        assert "anomalies" in result
        assert result["anomaly_count"] == 0
        print(f"\n[TC_05e] PASS — Missing execution handled gracefully")


# ═══════════════════════════════════════════════════════════════════════════════
# TC_06 — Variable Resolution
# ═══════════════════════════════════════════════════════════════════════════════

class TestVariableResolution:

    def test_variable_replacement(self):
        """TC_06: Verify {{var}} placeholders are replaced."""
        from modules.execution_engine import resolve_variables
        text = "Bearer {{auth_token}}"
        variables = {"auth_token": "abc123"}
        result = resolve_variables(text, variables)
        assert result == "Bearer abc123"
        print(f"\n[TC_06] PASS — Variable resolved: '{result}'")

    def test_variable_in_url(self):
        """TC_06b: Verify variable replacement in URL."""
        from modules.execution_engine import resolve_variables
        url = "http://api.test/users/{{user_id}}/profile"
        variables = {"user_id": "42"}
        result = resolve_variables(url, variables)
        assert result == "http://api.test/users/42/profile"
        print(f"\n[TC_06b] PASS — URL variable resolved: '{result}'")

    def test_extract_from_response(self):
        """TC_06c: Verify value extraction from response body."""
        from modules.execution_engine import extract_from_response
        response = {"token": "jwt-abc", "user": {"id": 99}}
        extract_vars = {"auth_token": "token", "uid": "user.id"}
        variables = {}
        variables = extract_from_response(response, extract_vars, variables)
        assert variables["auth_token"] == "jwt-abc"
        assert variables["uid"] == 99
        print(f"\n[TC_06c] PASS — Extracted variables: {variables}")

    def test_condition_evaluation_pass(self):
        """TC_06d: Verify condition evaluation for passing case."""
        from modules.execution_engine import evaluate_condition
        result = evaluate_condition("status == 200", 200, {})
        assert result is True
        print(f"\n[TC_06d] PASS — Condition 'status == 200' passed")

    def test_condition_evaluation_fail(self):
        """TC_06e: Verify condition evaluation for failing case."""
        from modules.execution_engine import evaluate_condition
        result = evaluate_condition("status == 200", 404, {})
        assert result is False
        print(f"\n[TC_06e] PASS — Condition 'status == 200' failed on 404")


# ═══════════════════════════════════════════════════════════════════════════════
# TC_07 — Metrics Computation
# ═══════════════════════════════════════════════════════════════════════════════

class TestMetrics:

    def test_metrics_missing_execution(self):
        """TC_07: Verify metrics handles missing execution gracefully."""
        from modules.metrics import compute_execution_metrics
        result = compute_execution_metrics("fake-exec-id")
        assert "error" in result
        print(f"\n[TC_07] PASS — Missing execution handled: {result}")

    def test_metrics_empty_summary(self):
        """TC_07b: Verify all-executions summary returns list."""
        from modules.metrics import get_all_executions_summary
        result = get_all_executions_summary()
        assert isinstance(result, list)
        print(f"\n[TC_07b] PASS — Summary returned {len(result)} executions")


# ═══════════════════════════════════════════════════════════════════════════════
# Run summary
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
