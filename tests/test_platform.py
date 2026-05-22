"""
Test suite for the FlowForge workflow execution and load simulation platform.
"""

import pytest
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from sqlmodel import SQLModel, Session, create_engine
import db as db_module  # import module so we can patch engine

TEST_DB_URL = "sqlite:///./test_platform.db"
_test_engine = create_engine(TEST_DB_URL)

# Patch the engine in db module and all submodules BEFORE any other imports
db_module.engine = _test_engine

from db import (
    Workflow, WorkflowStep, Execution, ExecutionTrace, MockApiConfig
)
from modules.workflow_manager import (
    create_workflow, get_workflow, list_workflows, delete_workflow,
    add_step, get_steps, delete_step, validate_workflow, update_workflow
)
from modules.mock_api import get_mock_response, create_mock_config
from modules.anomaly_detector import detect_anomalies, zscore_anomalies, iqr_anomalies
import modules.mock_api as mock_api_module
import modules.metrics as metrics_module
import modules.anomaly_detector as anomaly_module
import modules.execution_engine as execution_engine_module
import routers.executions as executions_router_module

# Patch engine in every module that imports it directly
mock_api_module.engine = _test_engine
metrics_module.engine = _test_engine
anomaly_module.engine = _test_engine
execution_engine_module.engine = _test_engine
executions_router_module.engine = _test_engine

# ─── Test DB setup ─────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def test_engine():
    SQLModel.metadata.create_all(_test_engine)
    yield _test_engine
    SQLModel.metadata.drop_all(_test_engine)
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
        # 10 tightly clustered values + one massive spike
        values = [100, 102, 98, 101, 99, 103, 97, 100, 101, 98, 2000]
        flags = zscore_anomalies(values)
        assert flags[-1] is True, f"Expected last value (2000) flagged, got flags={flags}"
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
        assert len(result["anomalies"]) == 0
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
# TC_08 — Execution Cancellation
# ═══════════════════════════════════════════════════════════════════════════════

class TestExecutionCancellation:

    @pytest.fixture(autouse=True)
    def _clear_registry(self):
        from modules.execution_engine import _running_tasks
        _running_tasks.clear()
        yield
        _running_tasks.clear()

    def test_cancel_running_execution(self, session):
        """TC_08: Cancel a mid-flight execution; verify status flips to 'cancelled'."""
        from sqlmodel import select
        from modules.execution_engine import run_execution, cancel_execution

        # Slow mock so the run is still in progress when we cancel.
        create_mock_config(
            session, "/test/cancel-slow", "GET", {"ok": True},
            latency_min=250, latency_max=350, error_rate=0.0, status_code=200,
        )

        wf = create_workflow(session, "Cancel Target")
        for i in range(3):
            add_step(session, wf.workflow_id, f"Slow{i}", "/test/cancel-slow", "GET", execution_order=i)

        ex_row = Execution(
            workflow_id=wf.workflow_id, concurrency=3, iterations=10,
            use_mock=True, status="pending",
        )
        session.add(ex_row); session.commit(); session.refresh(ex_row)
        exec_id = ex_row.execution_id

        async def scenario():
            task = asyncio.create_task(run_execution(exec_id))
            await asyncio.sleep(0.4)  # let the run register itself and start working
            assert cancel_execution(exec_id) is True, "cancel_execution should return True for a running task"
            try:
                await task
            except asyncio.CancelledError:
                pass

        asyncio.run(scenario())

        session.expire_all()
        final = session.exec(select(Execution).where(Execution.execution_id == exec_id)).first()
        assert final.status == "cancelled", f"expected 'cancelled', got {final.status!r}"
        assert final.end_time is not None, "end_time should be set on cancellation"
        assert cancel_execution(exec_id) is False, "second cancel should return False — task no longer registered"
        print(f"\n[TC_08] PASS — Execution cancelled mid-flight; status={final.status}")

    def test_cancel_unknown_execution(self):
        """TC_08b: cancel_execution returns False for an unknown execution_id."""
        from modules.execution_engine import cancel_execution
        assert cancel_execution("does-not-exist-xyz") is False
        print(f"\n[TC_08b] PASS — Unknown execution id returns False")

    def test_cancel_already_completed_execution(self):
        """TC_08c: cancel_execution returns False once the registered task has finished."""
        from modules.execution_engine import register_running, cancel_execution

        async def quick():
            return "done"

        async def scenario():
            task = asyncio.create_task(quick())
            register_running("completed-id", task)
            await task
            return cancel_execution("completed-id")

        result = asyncio.run(scenario())
        assert result is False
        print(f"\n[TC_08c] PASS — Cancel returns False after task completes")


# ═══════════════════════════════════════════════════════════════════════════════
# TC_09 — SSE Stream
# ═══════════════════════════════════════════════════════════════════════════════
#
# These tests hit FastAPI routes via TestClient, so they need the app's
# get_session dependency to resolve against the test DB. We override it inside
# each test's lifecycle.

def _get_test_client():
    """Build a TestClient with get_session overridden to use the test engine."""
    from fastapi.testclient import TestClient
    from main import app
    from db import get_session

    def _override():
        with Session(_test_engine) as s:
            yield s

    app.dependency_overrides[get_session] = _override
    return TestClient(app)


class TestSSEStream:

    def test_sse_unknown_execution_emits_error(self):
        """TC_09: SSE for unknown execution_id emits an error event then closes."""
        with _get_test_client() as c:
            with c.stream("GET", "/executions/no-such-exec-id/stream") as r:
                assert "text/event-stream" in r.headers.get("content-type", "")
                body = ""
                for chunk in r.iter_text():
                    body += chunk
                    if "event: error" in body:
                        break
                assert "event: error" in body, f"expected error event, got: {body[:200]}"
        print(f"\n[TC_09] PASS — Unknown execution emits error event")

    def test_sse_terminal_execution_replays_traces(self, session):
        """TC_09b: SSE for an already-terminal execution emits stored traces + status, then closes."""
        wf = create_workflow(session, "SSE Replay")
        ex = Execution(
            workflow_id=wf.workflow_id, status="success",
            concurrency=1, iterations=1,
        )
        session.add(ex); session.commit(); session.refresh(ex)
        for i in range(3):
            session.add(ExecutionTrace(
                execution_id=ex.execution_id,
                step_id=f"step-{i}", step_name=f"Step{i}",
                response_time=100.0 + i * 10, status_code=200,
                outcome="success", worker_id=0,
            ))
        session.commit()

        with _get_test_client() as c:
            with c.stream("GET", f"/executions/{ex.execution_id}/stream") as r:
                body = "".join(r.iter_text())

        assert body.count("event: trace") == 3, f"expected 3 trace events, got body: {body[:500]}"
        assert "event: status" in body
        assert '"status": "success"' in body
        print(f"\n[TC_09b] PASS — Terminal execution replayed 3 traces + status event")


# ═══════════════════════════════════════════════════════════════════════════════
# TC_10 — Workflow Import / Export
# ═══════════════════════════════════════════════════════════════════════════════

class TestImportExport:

    def test_export_round_trip_preserves_all_fields(self, session):
        """TC_10: Export → re-import preserves every step field including timeout_seconds."""
        with _get_test_client() as c:
            wf = c.post("/workflows", json={"name": "Roundtrip", "description": "test"}).json()
            wf_id = wf["workflow_id"]

            c.post(f"/workflows/{wf_id}/steps", json={
                "name": "Login",
                "endpoint": "http://localhost:8000/mock/login",
                "http_method": "POST",
                "headers": {"X-Trace-Id": "abc"},
                "body": {"user": "alice"},
                "extract_vars": {"token": "data.access_token"},
                "condition": "status == 200",
                "retry_count": 2,
                "execution_order": 0,
                "timeout_seconds": 15,
            })

            exp = c.get(f"/workflows/{wf_id}/export").json()
            assert exp["schema_version"] == "1.0"
            assert len(exp["steps"]) == 1
            step = exp["steps"][0]
            assert step["timeout_seconds"] == 15
            assert step["headers"] == {"X-Trace-Id": "abc"}
            assert step["extract_vars"] == {"token": "data.access_token"}

            imp = c.post("/workflows/import", json=exp)
            assert imp.status_code == 201
            new_wf_id = imp.json()["workflow_id"]
            assert new_wf_id != wf_id, "import must mint a new workflow_id"

            imported_steps = c.get(f"/workflows/{new_wf_id}/steps").json()
            assert len(imported_steps) == 1
            s = imported_steps[0]
            assert s["timeout_seconds"] == 15
            assert s["retry_count"] == 2
            assert s["condition"] == "status == 200"
            import json as _json
            assert _json.loads(s["headers"]) == {"X-Trace-Id": "abc"}
            assert _json.loads(s["extract_vars"]) == {"token": "data.access_token"}
        print(f"\n[TC_10] PASS — Round-trip preserved all step fields; new id minted")

    def test_import_rejects_unknown_schema_version(self):
        """TC_10b: Import with unknown schema_version returns 400."""
        with _get_test_client() as c:
            r = c.post("/workflows/import", json={
                "schema_version": "99.0",
                "workflow": {"name": "x"},
                "steps": [],
            })
            assert r.status_code == 400
            assert "schema_version" in r.json()["detail"]
        print(f"\n[TC_10b] PASS — Unknown schema_version rejected with 400")

    def test_export_missing_workflow_returns_404(self):
        """TC_10c: Export for unknown workflow_id returns 404."""
        with _get_test_client() as c:
            r = c.get("/workflows/no-such-wf/export")
            assert r.status_code == 404
        print(f"\n[TC_10c] PASS — Export for unknown workflow returns 404")


# ═══════════════════════════════════════════════════════════════════════════════
# TC_11 — Retry Backoff Math
# ═══════════════════════════════════════════════════════════════════════════════

class TestRetryBackoff:

    def test_backoff_doubles_per_attempt(self):
        """TC_11: First 5 attempts produce 0.5, 1, 2, 4, 8 seconds."""
        from modules.execution_engine import _retry_backoff_seconds
        assert _retry_backoff_seconds(0) == 0.5
        assert _retry_backoff_seconds(1) == 1.0
        assert _retry_backoff_seconds(2) == 2.0
        assert _retry_backoff_seconds(3) == 4.0
        assert _retry_backoff_seconds(4) == 8.0
        print(f"\n[TC_11] PASS — Backoff doubles per attempt: 0.5, 1, 2, 4, 8")

    def test_backoff_capped_at_30s(self):
        """TC_11b: Backoff caps at 30 seconds for high attempt numbers."""
        from modules.execution_engine import _retry_backoff_seconds
        # 0.5 * 2^7 = 64 → capped to 30
        assert _retry_backoff_seconds(7) == 30
        assert _retry_backoff_seconds(20) == 30
        assert _retry_backoff_seconds(100) == 30
        print(f"\n[TC_11b] PASS — Backoff capped at 30s for attempt ≥ 7")

    def test_backoff_zero_attempt_is_minimum(self):
        """TC_11c: Attempt 0 returns the 500 ms base wait."""
        from modules.execution_engine import _retry_backoff_seconds
        assert _retry_backoff_seconds(0) == 0.5
        print(f"\n[TC_11c] PASS — Attempt 0 = 500ms base wait")


# ═══════════════════════════════════════════════════════════════════════════════
# TC_12 — Anomaly Classification
# ═══════════════════════════════════════════════════════════════════════════════

class TestAnomalyClassification:

    def test_classify_latency_spike_critical(self):
        """TC_12: Z-score > 3.0 classifies as critical LATENCY_SPIKE."""
        from modules.anomaly_detector import classify_anomaly
        # response=1000, baseline=100, std=100 → z = 9.0
        result = classify_anomaly(
            response_time=1000.0, baseline_avg=100.0, baseline_std=100.0,
            outcome="success", step_error_rate=0.0,
        )
        assert result is not None
        assert result["type"] == "LATENCY_SPIKE"
        assert result["severity"] == "critical"
        assert result["confidence"] >= 0.7
        print(f"\n[TC_12] PASS — Critical latency spike classified (z=9, conf={result['confidence']})")

    def test_classify_performance_degradation_warning(self):
        """TC_12b: Z-score between 2.0 and 3.0 classifies as warning PERFORMANCE_DEGRADATION."""
        from modules.anomaly_detector import classify_anomaly
        # response=350, baseline=100, std=100 → z = 2.5
        result = classify_anomaly(
            response_time=350.0, baseline_avg=100.0, baseline_std=100.0,
            outcome="success", step_error_rate=0.0,
        )
        assert result is not None
        assert result["type"] == "PERFORMANCE_DEGRADATION"
        assert result["severity"] == "warning"
        print(f"\n[TC_12b] PASS — Performance degradation classified at z=2.5")

    def test_classify_failure_spike_critical(self):
        """TC_12c: Failure outcome with >50% error rate classifies as critical FAILURE_SPIKE."""
        from modules.anomaly_detector import classify_anomaly
        result = classify_anomaly(
            response_time=100.0, baseline_avg=100.0, baseline_std=10.0,
            outcome="fail", step_error_rate=0.8,
        )
        assert result is not None
        assert result["type"] == "FAILURE_SPIKE"
        assert result["severity"] == "critical"
        print(f"\n[TC_12c] PASS — Failure spike classified at error_rate=80%")

    def test_classify_elevated_error_rate_warning(self):
        """TC_12d: Failure outcome with 20-50% error rate classifies as warning ELEVATED_ERROR_RATE."""
        from modules.anomaly_detector import classify_anomaly
        result = classify_anomaly(
            response_time=100.0, baseline_avg=100.0, baseline_std=10.0,
            outcome="fail", step_error_rate=0.3,
        )
        assert result is not None
        assert result["type"] == "ELEVATED_ERROR_RATE"
        assert result["severity"] == "warning"
        print(f"\n[TC_12d] PASS — Elevated error rate classified at 30%")

    def test_classify_normal_returns_none(self):
        """TC_12e: Normal data (z<2, success outcome, low error rate) returns None."""
        from modules.anomaly_detector import classify_anomaly
        result = classify_anomaly(
            response_time=105.0, baseline_avg=100.0, baseline_std=10.0,
            outcome="success", step_error_rate=0.05,
        )
        assert result is None, f"expected None for normal data, got {result}"
        print(f"\n[TC_12e] PASS — Normal data returns None")


# ═══════════════════════════════════════════════════════════════════════════════
# Run summary
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])