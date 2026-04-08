from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select
from pydantic import BaseModel
from typing import Optional, List
import asyncio

from db import (
    init_db, get_session, Workflow, WorkflowStep,
    Execution, ExecutionTrace, MockApiConfig
)
from modules.workflow_manager import (
    create_workflow, get_workflow, list_workflows, delete_workflow,
    update_workflow, add_step, get_steps, delete_step, update_step,
    validate_workflow
)
from modules.execution_engine import run_execution
from modules.mock_api import create_mock_config, list_mock_configs, delete_mock_config
from modules.metrics import compute_execution_metrics, get_all_executions_summary
from modules.anomaly_detector import detect_anomalies, build_baseline

app = FastAPI(title="API Workflow Platform", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()


# ─── Pydantic request schemas ──────────────────────────────────────────────────

class WorkflowCreate(BaseModel):
    name: str
    description: Optional[str] = ""

class WorkflowUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class StepCreate(BaseModel):
    name: str
    endpoint: str
    http_method: str
    headers: Optional[dict] = {}
    body: Optional[dict] = {}
    extract_vars: Optional[dict] = {}
    condition: Optional[str] = None
    retry_count: Optional[int] = 0
    execution_order: Optional[int] = 0

class StepUpdate(BaseModel):
    name: Optional[str] = None
    endpoint: Optional[str] = None
    http_method: Optional[str] = None
    headers: Optional[dict] = None
    body: Optional[dict] = None
    extract_vars: Optional[dict] = None
    condition: Optional[str] = None
    retry_count: Optional[int] = None
    execution_order: Optional[int] = None

class ExecutionCreate(BaseModel):
    workflow_id: str
    concurrency: Optional[int] = 1
    iterations: Optional[int] = 1
    use_mock: Optional[bool] = False

class MockConfigCreate(BaseModel):
    endpoint: str
    http_method: str
    response_template: dict
    latency_min: Optional[int] = 0
    latency_max: Optional[int] = 100
    error_rate: Optional[float] = 0.0
    status_code: Optional[int] = 200


# ─── Workflow routes ───────────────────────────────────────────────────────────

@app.get("/workflows")
def list_wf(session: Session = Depends(get_session)):
    return list_workflows(session)

@app.post("/workflows", status_code=201)
def create_wf(body: WorkflowCreate, session: Session = Depends(get_session)):
    return create_workflow(session, body.name, body.description)

@app.get("/workflows/{workflow_id}")
def get_wf(workflow_id: str, session: Session = Depends(get_session)):
    wf = get_workflow(session, workflow_id)
    if not wf:
        raise HTTPException(404, "Workflow not found")
    return wf

@app.put("/workflows/{workflow_id}")
def update_wf(workflow_id: str, body: WorkflowUpdate, session: Session = Depends(get_session)):
    wf = update_workflow(session, workflow_id, body.name, body.description)
    if not wf:
        raise HTTPException(404, "Workflow not found")
    return wf

@app.delete("/workflows/{workflow_id}")
def delete_wf(workflow_id: str, session: Session = Depends(get_session)):
    if not delete_workflow(session, workflow_id):
        raise HTTPException(404, "Workflow not found")
    return {"deleted": True}

@app.get("/workflows/{workflow_id}/validate")
def validate_wf(workflow_id: str, session: Session = Depends(get_session)):
    return validate_workflow(session, workflow_id)


# ─── Step routes ───────────────────────────────────────────────────────────────

@app.get("/workflows/{workflow_id}/steps")
def list_steps(workflow_id: str, session: Session = Depends(get_session)):
    return get_steps(session, workflow_id)

@app.post("/workflows/{workflow_id}/steps", status_code=201)
def create_step(workflow_id: str, body: StepCreate, session: Session = Depends(get_session)):
    wf = get_workflow(session, workflow_id)
    if not wf:
        raise HTTPException(404, "Workflow not found")
    return add_step(
        session, workflow_id, body.name, body.endpoint, body.http_method,
        body.headers, body.body, body.extract_vars, body.condition,
        body.retry_count, body.execution_order
    )

@app.put("/steps/{step_id}")
def update_st(step_id: str, body: StepUpdate, session: Session = Depends(get_session)):
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    step = update_step(session, step_id, **data)
    if not step:
        raise HTTPException(404, "Step not found")
    return step

@app.delete("/steps/{step_id}")
def delete_st(step_id: str, session: Session = Depends(get_session)):
    if not delete_step(session, step_id):
        raise HTTPException(404, "Step not found")
    return {"deleted": True}


# ─── Execution routes ──────────────────────────────────────────────────────────

@app.post("/executions", status_code=201)
async def start_execution(body: ExecutionCreate, background_tasks: BackgroundTasks, session: Session = Depends(get_session)):
    wf = get_workflow(session, body.workflow_id)
    if not wf:
        raise HTTPException(404, "Workflow not found")

    validation = validate_workflow(session, body.workflow_id)
    if not validation["valid"]:
        raise HTTPException(400, f"Workflow invalid: {validation['errors']}")

    execution = Execution(
        workflow_id=body.workflow_id,
        concurrency=max(1, body.concurrency),
        iterations=max(1, body.iterations),
        use_mock=body.use_mock,
        status="pending",
    )
    session.add(execution)
    session.commit()
    session.refresh(execution)

    background_tasks.add_task(run_execution, execution.execution_id)
    return execution

@app.get("/executions")
def list_executions(workflow_id: Optional[str] = None):
    return get_all_executions_summary(workflow_id)

@app.get("/executions/{execution_id}")
def get_execution(execution_id: str, session: Session = Depends(get_session)):
    ex = session.exec(select(Execution).where(Execution.execution_id == execution_id)).first()
    if not ex:
        raise HTTPException(404, "Execution not found")
    return ex

@app.get("/executions/{execution_id}/traces")
def get_traces(execution_id: str, session: Session = Depends(get_session)):
    traces = list(session.exec(select(ExecutionTrace).where(ExecutionTrace.execution_id == execution_id)).all())
    return traces

@app.get("/executions/{execution_id}/metrics")
def get_metrics(execution_id: str):
    return compute_execution_metrics(execution_id)

@app.get("/executions/{execution_id}/anomalies")
def get_anomalies(execution_id: str):
    return detect_anomalies(execution_id)


# ─── Mock API routes ───────────────────────────────────────────────────────────

@app.get("/mock-configs")
def list_mocks(session: Session = Depends(get_session)):
    return list_mock_configs(session)

@app.post("/mock-configs", status_code=201)
def create_mock(body: MockConfigCreate, session: Session = Depends(get_session)):
    return create_mock_config(
        session, body.endpoint, body.http_method, body.response_template,
        body.latency_min, body.latency_max, body.error_rate, body.status_code
    )

@app.delete("/mock-configs/{mock_id}")
def delete_mock(mock_id: str, session: Session = Depends(get_session)):
    if not delete_mock_config(session, mock_id):
        raise HTTPException(404, "Mock config not found")
    return {"deleted": True}


# ─── Analytics & AI routes ─────────────────────────────────────────────────────

@app.get("/analytics")
def analytics_summary(workflow_id: Optional[str] = None):
    return get_all_executions_summary(workflow_id)

@app.get("/baseline/{workflow_id}")
def get_baseline(workflow_id: str):
    return build_baseline(workflow_id)


# ─── Dashboard summary ─────────────────────────────────────────────────────────

@app.get("/dashboard")
def dashboard(session: Session = Depends(get_session)):
    workflows = list_workflows(session)
    executions = get_all_executions_summary()

    total_executions = len(executions)
    active = sum(1 for e in executions if e["status"] == "running")
    success_rates = [e["success_rate"] for e in executions if e["total_steps"] > 0]
    avg_latencies = [e["avg_response_time"] for e in executions if e["avg_response_time"] > 0]

    return {
        "total_workflows": len(workflows),
        "total_executions": total_executions,
        "active_executions": active,
        "avg_success_rate": round(sum(success_rates) / len(success_rates), 2) if success_rates else 0,
        "avg_latency_ms": round(sum(avg_latencies) / len(avg_latencies), 2) if avg_latencies else 0,
        "recent_executions": executions[-5:][::-1],
    }
