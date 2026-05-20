import asyncio
import json
import time
import re
import base64
from datetime import datetime, timezone
from typing import Optional
import httpx
from sqlmodel import Session, select

from db import Execution, ExecutionTrace, WorkflowStep, engine
from modules.workflow_manager import get_steps, get_workflow
from modules.mock_api import get_mock_response


def _now():
    return datetime.now(timezone.utc)


# ─── Shared httpx client ───────────────────────────────────────────────────────
# Reused across executions so TCP/TLS handshakes are pooled, not paid per run.

_shared_client: Optional[httpx.AsyncClient] = None


def get_shared_client() -> httpx.AsyncClient:
    global _shared_client
    if _shared_client is None or _shared_client.is_closed:
        _shared_client = httpx.AsyncClient(
            limits=httpx.Limits(max_connections=200, max_keepalive_connections=50),
        )
    return _shared_client


async def close_shared_client() -> None:
    global _shared_client
    if _shared_client is not None and not _shared_client.is_closed:
        await _shared_client.aclose()
    _shared_client = None


# ─── Cancellation registry ─────────────────────────────────────────────────────
# Maps execution_id → asyncio.Task running run_execution(...) so the cancel
# route can call .cancel() on it. The runner registers itself on entry and
# clears the slot on exit.

_running_tasks: dict = {}


def register_running(execution_id: str, task) -> None:
    _running_tasks[execution_id] = task


def unregister_running(execution_id: str) -> None:
    _running_tasks.pop(execution_id, None)


def cancel_execution(execution_id: str) -> bool:
    task = _running_tasks.get(execution_id)
    if task is None or task.done():
        return False
    task.cancel()
    return True


# ─── Variable resolver ─────────────────────────────────────────────────────────

def resolve_variables(text: str, variables: dict) -> str:
    if not text:
        return text
    for k, v in variables.items():
        text = text.replace(f"{{{{{k}}}}}", str(v))
    return text


def extract_from_response(response_body: dict, extract_vars: dict, variables: dict) -> dict:
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
    if not condition:
        return True
    try:
        ctx = {"status": status_code, "response": response_body}
        return bool(eval(condition, {"__builtins__": {}}, ctx))
    except Exception:
        return True


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

    # Check if this step has a file attachment
    file_data_raw = getattr(step, 'file_data', None) or step.__dict__.get('file_data')
    # file_data stored as JSON: {"filename": "...", "content_b64": "...", "field_name": "file"}
    file_info = None
    try:
        extra = json.loads(step.extract_vars or "{}")
        # We store file info in a special __file__ key in extract_vars
        if "__file__" in extra:
            file_info = extra["__file__"]
    except Exception:
        pass

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
            timeout = float(getattr(step, "timeout_seconds", None) or 30)
            kwargs = {"headers": headers, "timeout": timeout}

            if file_info:
                # multipart/form-data upload
                file_bytes = base64.b64decode(file_info["content_b64"])
                field_name = file_info.get("field_name", "file")
                filename = file_info.get("filename", "upload.zip")
                files = {field_name: (filename, file_bytes, "application/octet-stream")}
                # Add any extra form fields from body
                try:
                    form_fields = json.loads(body_str) if body_str.strip() not in ("{}", "") else {}
                except Exception:
                    form_fields = {}
                kwargs["files"] = files
                if form_fields:
                    kwargs["data"] = form_fields
            elif method in ("POST", "PUT", "PATCH"):
                try:
                    body = json.loads(body_str) if body_str.strip() not in ("{}", "") else None
                except Exception:
                    body = None
                if body:
                    kwargs["json"] = body

            resp = await client.request(method, endpoint, **kwargs)
            status_code = resp.status_code
            try:
                response_body = resp.json()
            except Exception:
                response_body = {"raw": resp.text[:2000]}

    except Exception as e:
        error = str(e)

    elapsed_ms = (time.perf_counter() - start) * 1000

    condition_pass = evaluate_condition(step.condition, status_code, response_body)

    extract_vars = json.loads(step.extract_vars or "{}")
    # Remove special __file__ key before extraction
    extract_vars.pop("__file__", None)
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
        "response_body": json.dumps(response_body)[:2000],
        "error": error,
        "variables": variables,
    }


# ─── Single workflow instance runner ──────────────────────────────────────────

async def run_workflow_instance(
    execution_id: str,
    steps: list,
    use_mock: bool,
    worker_id: int,
    client: httpx.AsyncClient,
):
    variables = {}
    traces = []

    for step in steps:
        retries = max(0, step.retry_count)
        result = None
        for attempt in range(retries + 1):
            result = await execute_step(step, variables, use_mock, client)
            variables = result.pop("variables", variables)
            if result["outcome"] != "fail":
                break
            if attempt < retries:
                # Exponential backoff: 0.5s, 1s, 2s, 4s, 8s … capped at 30s.
                # Stops a flapping upstream from getting hammered.
                await asyncio.sleep(min(0.5 * (2 ** attempt), 30))

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

    with Session(engine) as session:
        for t in traces:
            trace = ExecutionTrace(**t)
            session.add(trace)
        session.commit()

    return traces


# ─── Worker: runs `iterations` workflow instances sequentially ────────────────

async def _worker(
    worker_id: int,
    iterations: int,
    execution_id: str,
    steps: list,
    use_mock: bool,
    client: httpx.AsyncClient,
) -> int:
    succeeded = 0
    for _ in range(iterations):
        try:
            await run_workflow_instance(execution_id, steps, use_mock, worker_id, client)
            succeeded += 1
        except Exception:
            # Swallow so the worker survives to run its remaining iterations.
            pass
    return succeeded


# ─── Main execution entry point ────────────────────────────────────────────────

async def run_execution(execution_id: str):
    register_running(execution_id, asyncio.current_task())
    try:
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

            steps = get_steps(session, workflow_id)

        client = get_shared_client()

        workers = [
            _worker(i, iterations, execution_id, steps, use_mock, client)
            for i in range(concurrency)
        ]
        results = await asyncio.gather(*workers, return_exceptions=True)

        total_iterations = concurrency * iterations
        completed = sum(r for r in results if isinstance(r, int))
        final_status = "failed" if completed == 0 and total_iterations > 0 else "success"

        with Session(engine) as session:
            execution = session.exec(
                select(Execution).where(Execution.execution_id == execution_id)
            ).first()
            execution.status = final_status
            execution.end_time = _now()
            session.add(execution)
            session.commit()

    except asyncio.CancelledError:
        with Session(engine) as session:
            ex = session.exec(
                select(Execution).where(Execution.execution_id == execution_id)
            ).first()
            if ex and ex.status not in ("success", "failed", "cancelled"):
                ex.status = "cancelled"
                ex.end_time = _now()
                session.add(ex)
                session.commit()
        raise
    finally:
        unregister_running(execution_id)