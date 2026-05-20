from sqlmodel import SQLModel, Field, create_engine, Session, select
from sqlalchemy import event
from typing import Optional
from datetime import datetime, timezone
import uuid

def _now():
    return datetime.now(timezone.utc)

DATABASE_URL = "sqlite:///./workflow_platform.db"
engine = create_engine(DATABASE_URL, echo=False)


@event.listens_for(engine, "connect")
def _set_sqlite_pragmas(dbapi_conn, _):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()


def get_session():
    with Session(engine) as session:
        yield session


def init_db():
    SQLModel.metadata.create_all(engine)
    _run_migrations()


def _run_migrations():
    """Lightweight in-place migrations for columns added after initial schema."""
    with engine.begin() as conn:
        step_cols = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(workflowstep)").fetchall()}
        if "timeout_seconds" not in step_cols:
            conn.exec_driver_sql(
                "ALTER TABLE workflowstep ADD COLUMN timeout_seconds INTEGER DEFAULT 30"
            )

        exec_cols = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(execution)").fetchall()}
        if "metrics_json" not in exec_cols:
            conn.exec_driver_sql("ALTER TABLE execution ADD COLUMN metrics_json TEXT")
        if "anomalies_json" not in exec_cols:
            conn.exec_driver_sql("ALTER TABLE execution ADD COLUMN anomalies_json TEXT")


# ─── Models ───────────────────────────────────────────────────────────────────

class WorkflowStep(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    workflow_id: str = Field(index=True)
    step_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    endpoint: str
    http_method: str  # GET POST PUT DELETE PATCH
    headers: Optional[str] = None   # JSON string
    body: Optional[str] = None      # JSON string
    extract_vars: Optional[str] = None  # JSON: {"var_name": "response.path"}
    condition: Optional[str] = None    # e.g. "status == 200"
    retry_count: int = Field(default=0)
    execution_order: int = Field(default=0)
    timeout_seconds: int = Field(default=30)


class Workflow(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    workflow_id: str = Field(default_factory=lambda: str(uuid.uuid4()), index=True, unique=True)
    name: str
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=_now)
    version: str = Field(default="1.0")


class Execution(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    execution_id: str = Field(default_factory=lambda: str(uuid.uuid4()), index=True, unique=True)
    workflow_id: str = Field(index=True)
    status: str = Field(default="pending")  # pending running success failed
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    concurrency: int = Field(default=1)
    iterations: int = Field(default=1)
    use_mock: bool = Field(default=False)
    error_message: Optional[str] = None
    metrics_json: Optional[str] = None    # cached compute_execution_metrics result
    anomalies_json: Optional[str] = None  # cached detect_anomalies result


class ExecutionTrace(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    trace_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    execution_id: str = Field(index=True)
    step_id: str
    step_name: str
    timestamp: datetime = Field(default_factory=_now)
    response_time: float = Field(default=0.0)  # ms
    status_code: Optional[int] = None
    outcome: str = Field(default="pending")  # success fail skipped
    response_body: Optional[str] = None
    error: Optional[str] = None
    worker_id: int = Field(default=0)


class MockApiConfig(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    mock_id: str = Field(default_factory=lambda: str(uuid.uuid4()), index=True, unique=True)
    endpoint: str
    http_method: str
    response_template: str  # JSON string
    latency_min: int = Field(default=0)    # ms
    latency_max: int = Field(default=100)  # ms
    error_rate: float = Field(default=0.0) # 0.0 to 1.0
    status_code: int = Field(default=200)