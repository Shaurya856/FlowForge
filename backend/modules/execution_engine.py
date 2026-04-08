import asyncio
import json
import time
import re
from datetime import datetime, timezone

def _now():
    return datetime.now(timezone.utc)
from typing import Optional
import httpx
from sqlmodel import Session, select

from db import Execution, ExecutionTrace, WorkflowStep, engine
from modules.workflow_manager import get_steps, get_workflow
from modules.mock_api import get_mock_response


# ─── Variable resolver ─────────────────────────────────────────────────────────

def resolve_variables(text: str, variables: dict) -> str:
    """Replace {{var_name}} placeholders with extracted values."""
    if not text:
        return text
    for k, v in variables.items():
        text = text.replace(f"{{{{{k}}}}}", str(v))
    return text


def extract_from_response(response_body: dict, extract_vars: dict, variables: dict) -> dict:
    """Extract values from response using dot-notation paths."""
    for var_name, path in extract_vars.items():
        try:
            parts = path.split(".")
            val = response_body
            for p in parts:
                if isinstance(val, dict):
                    val = val.get(p)
                elif isinstance(val, list) and p.isdigit():
                    val = val[int(p)]
                else:
                    val = None
                    break
            if val is not None:
                variables[var_name] = val
        except Exception:
            pass
    return variables


def evaluate_condition(condition: str, status_code: int, response_body: dict) -> bool:
    """Evaluate a simple condition string like 'status == 200'."""
    if not condition:
        return True
    try:
        ctx = {"status": status_code, "response": response_body}
        return bool(eval(condition, {"__builtins__": {}}, ctx))
    except Exception:
        return True  # If condition eval fails, proceed


# ─── Single step executor ──────────────────────────────────────────────────────

async def execute_step(
    step: WorkflowStep,
    variables: dict,
    use_mock: bool,
    client: httpx.AsyncClient,
) -> dict:
    method = step.http_method
    endpoint = resolve_variables(step.endpoint, variables)
    headers = json.loads(step.headers or "{}")
    body_raw = step.body or "{}"
    body_str = resolve_variables(body_raw, variables)
    body = json.loads(body_str) if body_str.strip() not in ("{}", "") else None

    # Resolve headers
    headers = {k: resolve_variables(v, variables) for k, v in headers.items()}

    start = time.perf_counter()
    status_code = 0
    response_body = {}
    error = None

    try:
        if use_mock:
            result = get_mock_response(endpoint, method)
            elapsed = result["latency"]
            await asyncio.sleep(elapsed / 1000)
            status_code = result["status_code"]
            response_body = result["body"]
        else:
            kwargs = {"headers": headers, "timeout": 30.0}
            if method in ("POST", "PUT", "PATCH") and body:
                kwargs["json"] = body
            resp = await client.request(method, endpoint, **kwargs)
            status_code = resp.status_code
            try:
                response_body = resp.json()
            except Exception:
                response_body = {"raw": resp.text}

    except Exception as e:
        error = str(e)

    elapsed_ms = (time.perf_counter() - start) * 1000

    # Check condition
    condition_pass = evaluate_condition(step.condition, status_code, response_body)

    # Extract variables from response
    extract_vars = json.loads(step.extract_vars or "{}")
    if extract_vars and isinstance(response_body, dict):
        variables = extract_from_response(response_body, extract_vars, variables)

    outcome = "success"
    if error:
        outcome = "fail"
    elif not condition_pass:
        outcome = "skipped"
    elif status_code >= 400:
        outcome = "fail"

    return {
        "status_code": status_code,
        "response_time": round(elapsed_ms, 2),
        "outcome": outcome,
        "response_body": json.dumps(response_body)[:2000],  # cap size
        "error": error,
        "variables": variables,
    }


# ─── Single workflow instance runner ──────────────────────────────────────────

async def run_workflow_instance(
    execution_id: str,
    workflow_id: str,
    use_mock: bool,
    worker_id: int = 0,
    client: Optional[httpx.AsyncClient] = None,
) -> list:
    with Session(engine) as session:
        steps = get_steps(session, workflow_id)

    variables = {}
    traces = []

    async def _run(c: httpx.AsyncClient):
        nonlocal variables
        for step in steps:
            retries = max(0, step.retry_count)
            result = None
            for attempt in range(retries + 1):
                result = await execute_step(step, variables, use_mock, c)
                variables = result.pop("variables", variables)
                if result["outcome"] != "fail":
                    break
                if attempt < retries:
                    await asyncio.sleep(0.1)  # reduced from 0.5s

            traces.append({
                "execution_id": execution_id,
                "step_id": step.step_id,
                "step_name": step.name,
                "response_time": result["response_time"],
                "status_code": result["status_code"],
                "outcome": result["outcome"],
                "response_body": result["response_body"],
                "error": result["error"],
                "worker_id": worker_id,
            })

            if result["outcome"] == "fail" and not use_mock:
                break

    if client is not None:
        await _run(client)
    else:
        async with httpx.AsyncClient() as c:
            await _run(c)

    # Traces are returned; caller is responsible for bulk-persisting
    return traces


# ─── Main execution entry point ────────────────────────────────────────────────

async def run_execution(execution_id: str):
    with Session(engine) as session:
        execution = session.exec(
            select(Execution).where(Execution.execution_id == execution_id)
        ).first()
        if not execution:
            return

        execution.status = "running"
        execution.start_time = _now()
        session.add(execution)
        session.commit()

        workflow_id = execution.workflow_id
        concurrency = execution.concurrency
        iterations = execution.iterations
        use_mock = execution.use_mock

    all_results = []

    limits = httpx.Limits(
        max_connections=min(concurrency, 100),
        max_keepalive_connections=min(concurrency, 20),
    )
    async with httpx.AsyncClient(limits=limits, timeout=30.0) as shared_client:
        # Run one round of `concurrency` workers per iteration.
        # This keeps at most `concurrency` coroutines alive at any time
        # instead of spawning all (concurrency * iterations) upfront.
        for iteration in range(iterations):
            round_results = await asyncio.gather(
                *[
                    run_workflow_instance(
                        execution_id, workflow_id, use_mock,
                        worker_id=w,
                        client=shared_client,
                    )
                    for w in range(concurrency)
                ],
                return_exceptions=True,
            )

            # Flush traces after each round — keeps memory flat
            round_traces = [t for r in round_results if isinstance(r, list) for t in r]
            if round_traces:
                with Session(engine) as session:
                    session.add_all([ExecutionTrace(**t) for t in round_traces])
                    session.commit()

            all_results.extend(round_results)

    total = concurrency * iterations
    failed = sum(1 for r in all_results if isinstance(r, Exception))
    final_status = "failed" if failed == total else "success"

    with Session(engine) as session:
        execution = session.exec(
            select(Execution).where(Execution.execution_id == execution_id)
        ).first()
        execution.status = final_status
        execution.end_time = _now()
        session.add(execution)
        session.commit()