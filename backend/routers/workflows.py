import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from db import get_session
from modules.workflow_manager import (
    create_workflow, get_workflow, list_workflows, delete_workflow,
    update_workflow, add_step, get_steps, delete_step, update_step,
    validate_workflow,
)
from routers.schemas import (
    WorkflowCreate, WorkflowUpdate, StepCreate, StepUpdate, WorkflowImport,
)

SUPPORTED_SCHEMA_VERSIONS = {"1.0"}

router = APIRouter()


# ─── Workflow routes ───────────────────────────────────────────────────────────

@router.get("/workflows")
def list_wf(session: Session = Depends(get_session)):
    return list_workflows(session)


@router.post("/workflows", status_code=201)
def create_wf(body: WorkflowCreate, session: Session = Depends(get_session)):
    return create_workflow(session, body.name, body.description)


@router.get("/workflows/{workflow_id}")
def get_wf(workflow_id: str, session: Session = Depends(get_session)):
    wf = get_workflow(session, workflow_id)
    if not wf:
        raise HTTPException(404, "Workflow not found")
    return wf


@router.put("/workflows/{workflow_id}")
def update_wf(workflow_id: str, body: WorkflowUpdate, session: Session = Depends(get_session)):
    wf = update_workflow(session, workflow_id, body.name, body.description)
    if not wf:
        raise HTTPException(404, "Workflow not found")
    return wf


@router.delete("/workflows/{workflow_id}")
def delete_wf(workflow_id: str, session: Session = Depends(get_session)):
    if not delete_workflow(session, workflow_id):
        raise HTTPException(404, "Workflow not found")
    return {"deleted": True}


@router.get("/workflows/{workflow_id}/validate")
def validate_wf(workflow_id: str, session: Session = Depends(get_session)):
    return validate_workflow(session, workflow_id)


@router.get("/workflows/{workflow_id}/export")
def export_wf(workflow_id: str, session: Session = Depends(get_session)):
    wf = get_workflow(session, workflow_id)
    if not wf:
        raise HTTPException(404, "Workflow not found")

    def _parse(s):
        try:
            return json.loads(s) if s else {}
        except json.JSONDecodeError:
            return {}

    steps = get_steps(session, workflow_id)
    return {
        "schema_version": "1.0",
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "workflow": {
            "name": wf.name,
            "description": wf.description or "",
        },
        "steps": [
            {
                "name": s.name,
                "endpoint": s.endpoint,
                "http_method": s.http_method,
                "headers": _parse(s.headers),
                "body": _parse(s.body),
                "extract_vars": _parse(s.extract_vars),
                "condition": s.condition,
                "retry_count": s.retry_count,
                "execution_order": s.execution_order,
                "timeout_seconds": s.timeout_seconds,
            }
            for s in steps
        ],
    }


@router.post("/workflows/import", status_code=201)
def import_wf(body: WorkflowImport, session: Session = Depends(get_session)):
    if body.schema_version not in SUPPORTED_SCHEMA_VERSIONS:
        raise HTTPException(
            400,
            f"Unsupported schema_version '{body.schema_version}'. Supported: {sorted(SUPPORTED_SCHEMA_VERSIONS)}",
        )

    wf = create_workflow(session, body.workflow.name, body.workflow.description or "")
    for step in body.steps:
        add_step(
            session, wf.workflow_id, step.name, step.endpoint, step.http_method,
            step.headers, step.body, step.extract_vars, step.condition,
            step.retry_count, step.execution_order, step.timeout_seconds,
        )
    return {
        "workflow_id": wf.workflow_id,
        "name": wf.name,
        "step_count": len(body.steps),
    }


# ─── Step routes ───────────────────────────────────────────────────────────────

@router.get("/workflows/{workflow_id}/steps")
def list_steps(workflow_id: str, session: Session = Depends(get_session)):
    return get_steps(session, workflow_id)


@router.post("/workflows/{workflow_id}/steps", status_code=201)
def create_step(workflow_id: str, body: StepCreate, session: Session = Depends(get_session)):
    wf = get_workflow(session, workflow_id)
    if not wf:
        raise HTTPException(404, "Workflow not found")
    return add_step(
        session, workflow_id, body.name, body.endpoint, body.http_method,
        body.headers, body.body, body.extract_vars, body.condition,
        body.retry_count, body.execution_order, body.timeout_seconds,
    )


@router.put("/steps/{step_id}")
def update_st(step_id: str, body: StepUpdate, session: Session = Depends(get_session)):
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    step = update_step(session, step_id, **data)
    if not step:
        raise HTTPException(404, "Step not found")
    return step


@router.delete("/steps/{step_id}")
def delete_st(step_id: str, session: Session = Depends(get_session)):
    if not delete_step(session, step_id):
        raise HTTPException(404, "Step not found")
    return {"deleted": True}
