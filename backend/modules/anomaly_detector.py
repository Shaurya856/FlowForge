import numpy as np
from sqlmodel import Session, select
from db import ExecutionTrace, engine
from typing import List, Dict, Optional
import statistics


# ─── Statistical anomaly detection (no LLM, runs on any laptop) ───────────────

def zscore_anomalies(values: List[float], threshold: float = 2.5) -> List[bool]:
    """Return boolean mask of anomalous values using Z-score."""
    if len(values) < 3:
        return [False] * len(values)
    mean = statistics.mean(values)
    stdev = statistics.stdev(values)
    if stdev == 0:
        return [False] * len(values)
    return [abs((v - mean) / stdev) > threshold for v in values]


def iqr_anomalies(values: List[float]) -> List[bool]:
    """Return boolean mask of anomalous values using IQR method."""
    if len(values) < 4:
        return [False] * len(values)
    arr = sorted(values)
    q1 = arr[len(arr) // 4]
    q3 = arr[(3 * len(arr)) // 4]
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    return [v < lower or v > upper for v in values]


def classify_anomaly(
    response_time: float,
    baseline_avg: float,
    baseline_std: float,
    outcome: str,
    step_error_rate: float,
) -> Optional[dict]:
    """Classify what type of anomaly this data point represents."""
    anomaly_type = None
    severity = "info"
    confidence = 0.0
    description = ""

    # Latency spike detection
    if baseline_std > 0:
        z = (response_time - baseline_avg) / baseline_std
        if z > 3.0:
            anomaly_type = "LATENCY_SPIKE"
            severity = "critical"
            confidence = min(0.99, 0.7 + (z - 3.0) * 0.1)
            pct = round((response_time - baseline_avg) / baseline_avg * 100, 1)
            description = f"Response time {response_time:.0f}ms is {pct}% above baseline ({baseline_avg:.0f}ms)"
        elif z > 2.0:
            anomaly_type = "PERFORMANCE_DEGRADATION"
            severity = "warning"
            confidence = 0.6 + (z - 2.0) * 0.1
            description = f"Response time elevated: {response_time:.0f}ms vs baseline {baseline_avg:.0f}ms"

    # Failure spike detection
    if outcome == "fail":
        if step_error_rate > 0.5:
            anomaly_type = "FAILURE_SPIKE"
            severity = "critical"
            confidence = min(0.95, step_error_rate)
            description = f"Step failure rate {step_error_rate*100:.0f}% exceeds threshold"
        elif step_error_rate > 0.2:
            if not anomaly_type:
                anomaly_type = "ELEVATED_ERROR_RATE"
                severity = "warning"
                confidence = step_error_rate
                description = f"Step error rate {step_error_rate*100:.0f}% is elevated"

    if not anomaly_type:
        return None

    return {
        "type": anomaly_type,
        "severity": severity,
        "confidence": round(confidence, 3),
        "description": description,
        "response_time": response_time,
        "baseline_avg": round(baseline_avg, 2),
    }


def detect_anomalies(execution_id: str) -> dict:
    """Run anomaly detection on a completed execution."""
    with Session(engine) as session:
        traces = list(
            session.exec(
                select(ExecutionTrace).where(ExecutionTrace.execution_id == execution_id)
            ).all()
        )

    if not traces:
        return {"anomalies": [], "summary": "No execution data found"}

    # Group by step
    step_groups: Dict[str, List[ExecutionTrace]] = {}
    for t in traces:
        step_groups.setdefault(t.step_name, []).append(t)

    anomalies = []

    for step_name, step_traces in step_groups.items():
        times = [t.response_time for t in step_traces]
        outcomes = [t.outcome for t in step_traces]
        error_rate = outcomes.count("fail") / len(outcomes) if outcomes else 0

        if len(times) < 2:
            continue

        mean_t = statistics.mean(times)
        std_t = statistics.stdev(times) if len(times) > 1 else 0

        # Run both detectors
        zscore_flags = zscore_anomalies(times)
        iqr_flags = iqr_anomalies(times)

        for i, trace in enumerate(step_traces):
            is_anomalous = zscore_flags[i] or iqr_flags[i] or trace.outcome == "fail"
            if not is_anomalous:
                continue

            anomaly = classify_anomaly(
                response_time=trace.response_time,
                baseline_avg=mean_t,
                baseline_std=std_t,
                outcome=trace.outcome,
                step_error_rate=error_rate,
            )
            if anomaly:
                anomaly.update({
                    "step_name": step_name,
                    "step_id": trace.step_id,
                    "trace_id": trace.trace_id,
                    "timestamp": trace.timestamp.isoformat(),
                    "worker_id": trace.worker_id,
                })
                anomalies.append(anomaly)

    # Sort by severity
    severity_order = {"critical": 0, "warning": 1, "info": 2}
    anomalies.sort(key=lambda x: severity_order.get(x["severity"], 3))

    # Build summary
    critical = sum(1 for a in anomalies if a["severity"] == "critical")
    warnings = sum(1 for a in anomalies if a["severity"] == "warning")

    if critical > 0:
        summary = f"⚠️ {critical} critical anomaly detected. Immediate attention recommended."
    elif warnings > 0:
        summary = f"⚡ {warnings} performance warning(s) detected."
    else:
        summary = "✅ No anomalies detected. Execution within normal parameters."

    return {
        "execution_id": execution_id,
        "anomaly_count": len(anomalies),
        "critical_count": critical,
        "warning_count": warnings,
        "summary": summary,
        "anomalies": anomalies,
    }


def build_baseline(workflow_id: str) -> dict:
    """Build a performance baseline from all past executions of a workflow."""
    with Session(engine) as session:
        # Get all execution IDs for this workflow
        from db import Execution
        executions = list(
            session.exec(select(Execution).where(Execution.workflow_id == workflow_id)).all()
        )
        exec_ids = [e.execution_id for e in executions if e.status == "success"]

        if not exec_ids:
            return {"error": "No successful executions to build baseline from"}

        all_traces = []
        for eid in exec_ids:
            traces = list(
                session.exec(select(ExecutionTrace).where(ExecutionTrace.execution_id == eid)).all()
            )
            all_traces.extend(traces)

    step_baselines = {}
    step_groups: Dict[str, List[float]] = {}
    for t in all_traces:
        step_groups.setdefault(t.step_name, []).append(t.response_time)

    for step_name, times in step_groups.items():
        step_baselines[step_name] = {
            "avg": round(statistics.mean(times), 2),
            "std": round(statistics.stdev(times) if len(times) > 1 else 0, 2),
            "min": round(min(times), 2),
            "max": round(max(times), 2),
            "sample_count": len(times),
        }

    return {
        "workflow_id": workflow_id,
        "execution_count": len(exec_ids),
        "step_baselines": step_baselines,
    }
