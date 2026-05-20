from typing import Optional

from fastapi import APIRouter, Depends
from sqlmodel import Session

from db import get_session
from modules.anomaly_detector import build_baseline
from modules.metrics import get_all_executions_summary
from modules.workflow_manager import list_workflows

router = APIRouter()


@router.get("/analytics")
def analytics_summary(workflow_id: Optional[str] = None):
    return get_all_executions_summary(workflow_id)


@router.get("/baseline/{workflow_id}")
def get_baseline(workflow_id: str):
    return build_baseline(workflow_id)


@router.get("/dashboard")
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
