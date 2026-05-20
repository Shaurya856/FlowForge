from sqlmodel import Session, select
from db import ExecutionTrace, Execution, engine
from typing import List, Dict, Optional
from datetime import datetime
import json
import statistics

TERMINAL_STATUSES = ("success", "failed", "cancelled")


def get_traces_for_execution(session: Session, execution_id: str) -> List[ExecutionTrace]:
    return list(
        session.exec(
            select(ExecutionTrace).where(ExecutionTrace.execution_id == execution_id)
        ).all()
    )


def compute_execution_metrics(execution_id: str) -> dict:
    with Session(engine) as session:
        execution = session.exec(
            select(Execution).where(Execution.execution_id == execution_id)
        ).first()
        if execution and execution.status in TERMINAL_STATUSES and execution.metrics_json:
            return json.loads(execution.metrics_json)
        traces = get_traces_for_execution(session, execution_id)

    if not traces:
        return {"error": "No traces found"}

    response_times = [t.response_time for t in traces]
    outcomes = [t.outcome for t in traces]

    total = len(traces)
    success = outcomes.count("success")
    failed = outcomes.count("fail")
    skipped = outcomes.count("skipped")

    duration_ms = None
    if execution and execution.start_time and execution.end_time:
        duration_ms = (execution.end_time - execution.start_time).total_seconds() * 1000

    # Per-step aggregation
    step_metrics = {}
    for t in traces:
        if t.step_name not in step_metrics:
            step_metrics[t.step_name] = {"times": [], "outcomes": []}
        step_metrics[t.step_name]["times"].append(t.response_time)
        step_metrics[t.step_name]["outcomes"].append(t.outcome)

    step_summary = {}
    for step_name, data in step_metrics.items():
        times = data["times"]
        step_summary[step_name] = {
            "avg_response_time": round(statistics.mean(times), 2),
            "min_response_time": round(min(times), 2),
            "max_response_time": round(max(times), 2),
            "success_count": data["outcomes"].count("success"),
            "fail_count": data["outcomes"].count("fail"),
        }

    result = {
        "execution_id": execution_id,
        "total_steps": total,
        "success": success,
        "failed": failed,
        "skipped": skipped,
        "success_rate": round(success / total * 100, 2) if total > 0 else 0,
        "error_rate": round(failed / total * 100, 2) if total > 0 else 0,
        "avg_response_time": round(statistics.mean(response_times), 2) if response_times else 0,
        "min_response_time": round(min(response_times), 2) if response_times else 0,
        "max_response_time": round(max(response_times), 2) if response_times else 0,
        "p95_response_time": round(sorted(response_times)[int(len(response_times) * 0.95)] if len(response_times) >= 20 else max(response_times), 2) if response_times else 0,
        "total_duration_ms": round(duration_ms, 2) if duration_ms else None,
        "step_summary": step_summary,
        "timeline": [
            {
                "step_name": t.step_name,
                "timestamp": t.timestamp.isoformat(),
                "response_time": t.response_time,
                "outcome": t.outcome,
                "status_code": t.status_code,
                "worker_id": t.worker_id,
            }
            for t in sorted(traces, key=lambda x: x.timestamp)
        ],
    }

    if execution and execution.status in TERMINAL_STATUSES and not execution.metrics_json:
        with Session(engine) as session:
            ex = session.exec(
                select(Execution).where(Execution.execution_id == execution_id)
            ).first()
            if ex:
                ex.metrics_json = json.dumps(result)
                session.add(ex)
                session.commit()

    return result


def get_all_executions_summary(workflow_id: Optional[str] = None) -> List[dict]:
    with Session(engine) as session:
        query = select(Execution)
        if workflow_id:
            query = query.where(Execution.workflow_id == workflow_id)
        executions = list(session.exec(query).all())

    summaries = []
    for ex in executions:
        with Session(engine) as session:
            traces = get_traces_for_execution(session, ex.execution_id)

        total = len(traces)
        success = sum(1 for t in traces if t.outcome == "success")
        response_times = [t.response_time for t in traces]

        summaries.append({
            "execution_id": ex.execution_id,
            "workflow_id": ex.workflow_id,
            "status": ex.status,
            "start_time": ex.start_time.isoformat() if ex.start_time else None,
            "end_time": ex.end_time.isoformat() if ex.end_time else None,
            "total_steps": total,
            "success_rate": round(success / total * 100, 2) if total > 0 else 0,
            "avg_response_time": round(statistics.mean(response_times), 2) if response_times else 0,
            "concurrency": ex.concurrency,
            "iterations": ex.iterations,
        })

    return summaries
