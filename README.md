# FlowForge — Scenario-Based API Workflow Execution Platform

A self-hosted load-testing and API orchestration tool. Define multi-step workflows, run them at configurable concurrency, stream traces live, and detect performance anomalies — all from a single laptop.

> **Single-user by design.** FlowForge is a single-developer tool meant to run on `localhost` only. There is no authentication, no multi-user support, and no plans for either — that's intentional, not a missing feature. Don't expose the backend on a public interface.

---

## Quick Start

### Docker (recommended)

Requires [Docker Desktop](https://www.docker.com/products/docker-desktop/) or Docker Engine + Compose plugin.

```bash
docker compose up --build
```

UI available at: http://localhost:3000

The SQLite database is stored in a named Docker volume (`db_data`) and persists across restarts. To wipe it: `docker compose down -v`.

---

### Manual setup

#### 1. Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```
API docs auto-available at: http://localhost:8000/docs

#### 2. Frontend
```bash
cd frontend
npm install
npm run dev
```
UI available at: http://localhost:5173

#### 3. Tests
```bash
cd backend
source venv/bin/activate        # Windows: venv\Scripts\activate
cd ../tests
pytest test_platform.py -v
```

---

## Project Structure
```
project/
├── backend/
│   ├── main.py                    # FastAPI app shell + lifecycle hooks
│   ├── db.py                      # SQLModel models + lightweight migrations
│   ├── requirements.txt
│   ├── routers/
│   │   ├── schemas.py             # Pydantic request bodies
│   │   ├── workflows.py           # /workflows + /steps routes
│   │   ├── executions.py          # /executions + SSE stream + metrics
│   │   ├── mock.py                # /mock-configs routes
│   │   └── dashboard.py           # /dashboard + /analytics + /baseline
│   └── modules/
│       ├── workflow_manager.py    # Workflow + Step CRUD
│       ├── execution_engine.py    # Async workflow runner + shared httpx client
│       ├── mock_api.py            # Mock API server
│       ├── metrics.py             # Metrics computation (with terminal-status cache)
│       └── anomaly_detector.py    # Z-score + IQR anomaly detection (cached)
├── frontend/
│   └── src/
│       ├── App.tsx                # Shell + routing
│       ├── App.css                # Global dark theme
│       ├── api/client.ts          # Axios API calls
│       ├── components/
│       │   └── ErrorBoundary.tsx  # Catches render errors per page
│       └── pages/
│           ├── Dashboard/         # Overview + recent executions
│           ├── Workflows/         # Workflows.tsx + WorkflowRow + StepRow + AddStepModal + EditStepModal
│           ├── Execution/         # Run panel + SSE trace viewer
│           ├── Analytics/         # Charts + metrics
│           ├── AIInsights/        # Anomaly detection
│           └── MockAPI/           # Mock endpoint config
└── tests/
    └── test_platform.py           # 49 pytest test cases (TC_01–TC_12)
```

---

## Usage Guide

### The mental model

- **Workflow** = an ordered list of HTTP **steps**, like a recipe (login → fetch → submit).
- **Execution** = a single run of a workflow. You can run the same workflow many times with different `concurrency` and `iterations` settings.
- **Trace** = the recorded outcome of one step inside one execution (status, latency, response body).
- `concurrency = N` workers run in parallel, each repeating the workflow `iterations` times sequentially. Total runs = `concurrency × iterations`, but only `concurrency` are in flight at any moment.

### Page-by-page

| Page | What it's for |
|---|---|
| **Dashboard** | Top-level KPIs and the 5 most recent executions. Start here to see if anything is on fire. |
| **Workflows** | Create / edit / delete workflows, add steps, validate, import/export JSON. |
| **Execution** | Pick a workflow, set concurrency/iterations, click Run, watch traces stream in live. |
| **Analytics** | Charts and percentile metrics for any past execution. Cached after the run finishes. |
| **AI Insights** | Statistical anomaly detection (Z-score, IQR, error-rate). Run after an execution completes. |
| **Mock API** | Configure custom mock endpoints if the built-in ones at `/mock/*` aren't enough. |

### Step 1 — Create a workflow

1. **Workflows → New Workflow**, give it a name and description.
2. Click the row to expand it, then **Add Step**.
3. For each step fill in:
   - **Endpoint URL** — full URL, e.g. `https://api.example.com/login`. Can include `{{variables}}`.
   - **HTTP Method** — GET / POST / PUT / PATCH / DELETE.
   - **Headers** — JSON object, e.g. `{"Authorization": "Bearer {{token}}"}`.
   - **Body** — JSON object for POST/PUT/PATCH.
   - **Extract Variables** — JSON map of `{"var_name": "dot.path.in.response"}`. See below.
   - **Condition** — optional, e.g. `status == 200`. If false, the step is marked `skipped`.
   - **Execution Order** — lower numbers run first.
   - **Retry Count** — 0–5. Each retry waits 500 ms before firing.
   - **Timeout (seconds)** — per-step HTTP timeout, default 30.
4. Click **Validate** on the workflow row to check for missing endpoints / invalid methods.

### Step 2 — Extract and reuse variables

This is the bit that makes multi-step workflows work.

Say step 0 (`POST /login`) returns:
```json
{ "data": { "access_token": "eyJhbGc..." }, "user_id": 42 }
```

In step 0's **Extract Variables** field, set:
```json
{ "token": "data.access_token", "uid": "user_id" }
```

Now in step 1 you can use `{{token}}` and `{{uid}}` anywhere — endpoint URL, headers, body. Variables persist for the lifetime of one workflow instance (so each iteration starts with a clean slate).

### Step 3 — Run it

Go to **Execution**, pick the workflow:
- Toggle **Use Mock API** on for a dry run against the built-in `/mock/*` endpoints — no real network calls.
- Set **Concurrency** (parallel workers) and **Iterations** (repeats per worker). Start with 1×1.
- Click **Run Workflow**. Traces stream in live via SSE — no polling, no refresh button needed.

### Step 4 — Read the results

- **Execution panel** shows each trace as it happens: step name, outcome, status code, response time, worker ID.
- **Analytics** shows per-step averages, p95, and a response-time-over-time chart.
- **AI Insights → Run Anomaly Detection** highlights latency spikes (Z > 3σ), persistent degradations, and elevated error rates.

For a deeper load-testing playbook (scaling up safely, interpreting p95 vs p99, when to stop), see [GUIDE.md](GUIDE.md).

### Sample Workflow (built-in mocks)

1. **Workflows → New Workflow**: "User Login Flow"
2. Add steps:
   - Step 0: POST `http://localhost:8000/mock/login` — extract `{"auth_token": "token"}`
   - Step 1: GET `http://localhost:8000/mock/users` — headers `{"Authorization": "Bearer {{auth_token}}"}`
   - Step 2: POST `http://localhost:8000/mock/data` — body `{"user": "{{auth_token}}"}`
3. **Execution** → select workflow, **Use Mock API** ON, click Run
4. **Analytics** → select execution to see metrics
5. **AI Insights** → select execution → Run Anomaly Detection

---

## Importing & Exporting Workflows

Workflows can be saved to a JSON file and re-created on any machine that runs FlowForge. Useful for sharing test scenarios with teammates, committing them to version control, or backing up before a risky edit.

### Export

In the Workflows page, click the **download icon** on the row of the workflow you want to export. The browser downloads `<workflow-name>.json`.

Programmatically:
```bash
curl http://localhost:8000/workflows/<workflow_id>/export -o my-flow.json
```

### Import

In the Workflows page, click **Import** in the top right, pick a `.json` file. A new workflow is created (fresh UUID — your original is untouched even if you import on the same machine).

Programmatically:
```bash
curl -X POST http://localhost:8000/workflows/import \
  -H "Content-Type: application/json" \
  -d @my-flow.json
```

### JSON schema

```json
{
  "schema_version": "1.0",
  "exported_at": "2026-05-21T12:34:56+00:00",
  "workflow": {
    "name": "User Login Flow",
    "description": "Auth + fetch + submit"
  },
  "steps": [
    {
      "name": "Login",
      "endpoint": "http://localhost:8000/mock/login",
      "http_method": "POST",
      "headers": {},
      "body": {},
      "extract_vars": { "token": "token" },
      "condition": "status == 200",
      "retry_count": 1,
      "execution_order": 0,
      "timeout_seconds": 30
    }
  ]
}
```

`schema_version` is currently `"1.0"`. The import endpoint rejects unknown versions with HTTP 400 so you'll never silently drop fields when the schema evolves.

---

## AI Anomaly Detection (no LLM required)

Detection uses two purely statistical methods:
- **Z-score**: flags response times > 2.5 standard deviations from step mean
- **IQR**: flags values outside 1.5× the interquartile range
- **Error rate**: classifies steps with > 20% failure rate as anomalous

All computation is local — no API keys, no GPU, no cloud dependency.

---

## Live Execution Traces (Server-Sent Events)

The Execution page streams traces in real time via the `GET /executions/{id}/stream` SSE endpoint instead of polling. The browser opens a single long-lived connection; the backend pushes a `trace` event for each new step result and a `status` event when the execution transitions state. The stream closes automatically once status reaches `success` or `failed`.

---

## Execution Concurrency Model

The execution engine now spawns exactly `concurrency` long-lived worker coroutines, each of which runs the workflow `iterations` times **sequentially**. Total workflow runs are still `concurrency × iterations`, but only `concurrency` are ever in flight at once. This caps open HTTP sockets, prevents file-descriptor exhaustion on macOS (default 256 fds), and gives the load-test numbers a meaningful "N concurrent users" interpretation.

A single `httpx.AsyncClient` is shared across every execution (see `get_shared_client` / `close_shared_client` in `execution_engine.py`). TCP connections and TLS handshakes are pooled across runs instead of being torn down and rebuilt per workflow instance. The client is closed on FastAPI shutdown.

## Retry Backoff

When a step fails and `retry_count > 0`, the engine waits between attempts using exponential backoff:

| Attempt | Wait before next try |
|---|---|
| 1 | 0.5 s |
| 2 | 1 s |
| 3 | 2 s |
| 4 | 4 s |
| 5 | 8 s (max retry) |

Capped at 30 s. Replaces the previous flat 500 ms wait so a flapping upstream isn't hammered by the same pattern over and over.

---

## Execution Cancellation

A running execution can be stopped from the **Execution** page — when the selected execution is `running` or `pending`, a **Cancel** button appears in the Traces card. Behind the scenes:

- The engine keeps a module-level `_running_tasks` dict mapping `execution_id` → `asyncio.Task`.
- `POST /executions/{id}/cancel` looks up the task and calls `.cancel()`, which raises `CancelledError` at the next `await`. The error propagates through `asyncio.gather`, through `_worker`, through `run_workflow_instance`, all the way down to the in-flight `httpx` request — every open socket is closed cleanly.
- The `except asyncio.CancelledError` block in `run_execution` flips the status to `cancelled` and sets `end_time` before re-raising.
- `cancelled` is treated as a terminal status by the SSE stream, metric cache, and anomaly cache, so the UI immediately stops polling and any subsequent metric requests use whatever traces were recorded before the cancel landed.

Cancelling a finished execution returns `409 Conflict` with the current status. Cancelling an unknown execution returns `404`.

---

## Per-Step Timeout

Every step has a `timeout_seconds` field (default 30) configurable from the Workflows page next to Retry Count. The value is passed straight through to `httpx`, so a hanging upstream server can no longer pin a worker indefinitely. Existing databases get the column added automatically by the startup migration in `db.py`.

---

## Cached Metrics & Anomalies

Once an execution reaches a terminal status (`success` or `failed`), the first call to `/executions/{id}/metrics` or `/executions/{id}/anomalies` computes the result *and* persists it into `Execution.metrics_json` / `Execution.anomalies_json`. Subsequent reads return the cached JSON directly instead of re-aggregating the trace table. Running executions still compute fresh on every request since the data is still moving.

---

## SQLite Concurrency (WAL Mode)

The database engine in `backend/db.py` enables Write-Ahead Logging on every connection:

- `PRAGMA journal_mode=WAL` — readers don't block writers and vice versa, so concurrent trace inserts during a high-concurrency execution don't serialize behind a single lock.
- `PRAGMA synchronous=NORMAL` — safe under WAL and noticeably faster than the default `FULL` for trace-heavy workloads.

This is set once at startup and persists in the database file. Two sidecar files (`workflow_platform.db-wal` and `workflow_platform.db-shm`) are created automatically and managed by SQLite.
