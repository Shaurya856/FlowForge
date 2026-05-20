from pydantic import BaseModel
from typing import List, Optional


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
    timeout_seconds: Optional[int] = 30


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
    timeout_seconds: Optional[int] = None


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


# ─── Export / Import ───────────────────────────────────────────────────────────

class WorkflowExportMeta(BaseModel):
    name: str
    description: Optional[str] = ""


class WorkflowImport(BaseModel):
    schema_version: str = "1.0"
    workflow: WorkflowExportMeta
    steps: List[StepCreate] = []
