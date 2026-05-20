from sqlmodel import Session, select
from db import Workflow, WorkflowStep
from typing import List, Optional
import json


# ─── Workflow CRUD ─────────────────────────────────────────────────────────────

def create_workflow(session: Session, name: str, description: str = "") -> Workflow:
    wf = Workflow(name=name, description=description)
    session.add(wf)
    session.commit()
    session.refresh(wf)
    return wf


def get_workflow(session: Session, workflow_id: str) -> Optional[Workflow]:
    return session.exec(select(Workflow).where(Workflow.workflow_id == workflow_id)).first()


def list_workflows(session: Session) -> List[Workflow]:
    return list(session.exec(select(Workflow)).all())


def delete_workflow(session: Session, workflow_id: str) -> bool:
    wf = get_workflow(session, workflow_id)
    if not wf:
        return False
    # delete steps
    steps = get_steps(session, workflow_id)
    for s in steps:
        session.delete(s)
    session.delete(wf)
    session.commit()
    return True


def update_workflow(session: Session, workflow_id: str, name: str = None, description: str = None) -> Optional[Workflow]:
    wf = get_workflow(session, workflow_id)
    if not wf:
        return None
    if name:
        wf.name = name
    if description is not None:
        wf.description = description
    session.add(wf)
    session.commit()
    session.refresh(wf)
    return wf


# ─── Step CRUD ─────────────────────────────────────────────────────────────────

def add_step(
    session: Session,
    workflow_id: str,
    name: str,
    endpoint: str,
    http_method: str,
    headers: dict = None,
    body: dict = None,
    extract_vars: dict = None,
    condition: str = None,
    retry_count: int = 0,
    execution_order: int = 0,
    timeout_seconds: int = 30,
) -> WorkflowStep:
    step = WorkflowStep(
        workflow_id=workflow_id,
        name=name,
        endpoint=endpoint,
        http_method=http_method.upper(),
        headers=json.dumps(headers or {}),
        body=json.dumps(body or {}),
        extract_vars=json.dumps(extract_vars or {}),
        condition=condition,
        retry_count=retry_count,
        execution_order=execution_order,
        timeout_seconds=timeout_seconds if timeout_seconds is not None else 30,
    )
    session.add(step)
    session.commit()
    session.refresh(step)
    return step


def get_steps(session: Session, workflow_id: str) -> List[WorkflowStep]:
    steps = session.exec(
        select(WorkflowStep)
        .where(WorkflowStep.workflow_id == workflow_id)
        .order_by(WorkflowStep.execution_order)
    ).all()
    return list(steps)


def delete_step(session: Session, step_id: str) -> bool:
    step = session.exec(select(WorkflowStep).where(WorkflowStep.step_id == step_id)).first()
    if not step:
        return False
    session.delete(step)
    session.commit()
    return True


def update_step(session: Session, step_id: str, **kwargs) -> Optional[WorkflowStep]:
    step = session.exec(select(WorkflowStep).where(WorkflowStep.step_id == step_id)).first()
    if not step:
        return None
    for k, v in kwargs.items():
        if k in ("headers", "body", "extract_vars") and isinstance(v, dict):
            v = json.dumps(v)
        if hasattr(step, k):
            setattr(step, k, v)
    session.add(step)
    session.commit()
    session.refresh(step)
    return step


def validate_workflow(session: Session, workflow_id: str) -> dict:
    wf = get_workflow(session, workflow_id)
    if not wf:
        return {"valid": False, "errors": ["Workflow not found"]}
    steps = get_steps(session, workflow_id)
    errors = []
    if len(steps) == 0:
        errors.append("Workflow has no steps")
    for s in steps:
        if not s.endpoint:
            errors.append(f"Step '{s.name}' missing endpoint")
        if s.http_method not in ("GET", "POST", "PUT", "DELETE", "PATCH"):
            errors.append(f"Step '{s.name}' has invalid HTTP method: {s.http_method}")
    return {"valid": len(errors) == 0, "errors": errors}
