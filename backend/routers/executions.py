import asyncio
import json
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select

from db import Execution, ExecutionTrace, engine, get_session
from modules.anomaly_detector import detect_anomalies
from modules.execution_engine import cancel_execution, run_execution
from modules.metrics import compute_execution_metrics, get_all_executions_summary
from modules.workflow_manager import get_workflow, validate_workflow
from routers.schemas import ExecutionCreate

TERMINAL_STATUSES = ("success", "failed", "cancelled")

router = APIRouter()


@router.post("/executions", status_code=201)
async def start_execution(
    body: ExecutionCreate,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
):
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


@router.get("/executions")
def list_executions(workflow_id: Optional[str] = None):
    return get_all_executions_summary(workflow_id)


@router.get("/executions/{execution_id}")
def get_execution(execution_id: str, session: Session = Depends(get_session)):
    ex = session.exec(select(Execution).where(Execution.execution_id == execution_id)).first()
    if not ex:
        raise HTTPException(404, "Execution not found")
    return ex


@router.get("/executions/{execution_id}/traces")
def get_traces(execution_id: str, session: Session = Depends(get_session)):
    traces = list(
        session.exec(select(ExecutionTrace).where(ExecutionTrace.execution_id == execution_id)).all()
    )
    return traces


@router.post("/executions/{execution_id}/cancel")
def cancel_execution_route(execution_id: str, session: Session = Depends(get_session)):
    ex = session.exec(select(Execution).where(Execution.execution_id == execution_id)).first()
    if not ex:
        raise HTTPException(404, "Execution not found")
    if ex.status in TERMINAL_STATUSES:
        raise HTTPException(409, f"Execution is already {ex.status}")
    if not cancel_execution(execution_id):
        # Task isn't tracked — likely never started or already finished between
        # the status check and now. Mark as cancelled anyway so the UI is consistent.
        ex.status = "cancelled"
        session.add(ex)
        session.commit()
        return {"cancelling": False, "execution_id": execution_id, "note": "task not running; status marked cancelled"}
    return {"cancelling": True, "execution_id": execution_id}


@router.get("/executions/{execution_id}/stream")
async def stream_traces(execution_id: str):
    async def event_generator():
        seen_ids: set = set()
        last_status = None

        while True:
            with Session(engine) as session:
                ex = session.exec(
                    select(Execution).where(Execution.execution_id == execution_id)
                ).first()

                if not ex:
                    yield f"event: error\ndata: {json.dumps({'message': 'Execution not found'})}\n\n"
                    return

                traces = list(
                    session.exec(
                        select(ExecutionTrace).where(ExecutionTrace.execution_id == execution_id)
                    ).all()
                )

            for trace in traces:
                if trace.trace_id not in seen_ids:
                    seen_ids.add(trace.trace_id)
                    payload = {
                        "trace_id": trace.trace_id,
                        "execution_id": trace.execution_id,
                        "step_id": trace.step_id,
                        "step_name": trace.step_name,
                        "timestamp": trace.timestamp.isoformat(),
                        "response_time": trace.response_time,
                        "status_code": trace.status_code,
                        "outcome": trace.outcome,
                        "response_body": trace.response_body,
                        "error": trace.error,
                        "worker_id": trace.worker_id,
                    }
                    yield f"event: trace\ndata: {json.dumps(payload)}\n\n"

            if ex.status != last_status:
                last_status = ex.status
                yield f"event: status\ndata: {json.dumps({'status': ex.status})}\n\n"

            if ex.status in TERMINAL_STATUSES:
                return

            await asyncio.sleep(0.3)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.get("/executions/{execution_id}/metrics")
def get_metrics(execution_id: str):
    return compute_execution_metrics(execution_id)


@router.get("/executions/{execution_id}/anomalies")
def get_anomalies(execution_id: str):
    return detect_anomalies(execution_id)
