# FlowForge — Scenario-Based API Workflow Execution Platform
## BCSE301P Software Engineering Lab | Shaurya Maloo 23BAI0185

---

## Quick Start

### 1. Backend
```bash
cd backend
pip install fastapi uvicorn sqlmodel aiosqlite httpx scikit-learn numpy python-multipart pydantic
uvicorn main:app --reload --port 8000
```
API docs auto-available at: http://localhost:8000/docs

### 2. Frontend
```bash
cd frontend
npm install
npm run dev
```
UI available at: http://localhost:5173

### 3. Tests
```bash
cd tests
pip install pytest
pytest test_platform.py -v
```

---

## Project Structure
```
project/
├── backend/
│   ├── main.py                    # FastAPI app + all routes
│   ├── db.py                      # SQLModel database models
│   ├── requirements.txt
│   └── modules/
│       ├── workflow_manager.py    # Workflow + Step CRUD
│       ├── execution_engine.py    # Async workflow runner
│       ├── mock_api.py            # Mock API server
│       ├── metrics.py             # Metrics computation
│       └── anomaly_detector.py    # Z-score + IQR anomaly detection
├── frontend/
│   └── src/
│       ├── App.tsx                # Shell + routing
│       ├── App.css                # Global dark theme
│       ├── api/client.ts          # Axios API calls
│       └── pages/
│           ├── Dashboard/         # Overview + recent executions
│           ├── Workflows/         # Workflow + step builder
│           ├── Execution/         # Run + trace viewer
│           ├── Analytics/         # Charts + metrics
│           ├── AIInsights/        # Anomaly detection
│           └── MockAPI/           # Mock endpoint config
└── tests/
    └── test_platform.py           # 25 pytest test cases
```

---

## Sample Workflow (uses built-in mock endpoints)

1. Go to **Workflows** → Create workflow "User Login Flow"
2. Add steps:
   - Step 0: POST `http://localhost:8000/mock/login` — extract `{"auth_token": "token"}`
   - Step 1: GET `http://localhost:8000/mock/users` — headers `{"Authorization": "Bearer {{auth_token}}"}`
   - Step 2: POST `http://localhost:8000/mock/data` — body `{"user": "{{auth_token}}"}`
3. Go to **Execution** → select workflow, enable "Use Mock API", click Run
4. Go to **Analytics** → select execution to see metrics
5. Go to **AI Insights** → select execution → Run Anomaly Detection

---

## AI Anomaly Detection (no LLM required)

Detection uses two purely statistical methods:
- **Z-score**: flags response times > 2.5 standard deviations from step mean
- **IQR**: flags values outside 1.5× the interquartile range
- **Error rate**: classifies steps with > 20% failure rate as anomalous

All computation is local — no API keys, no GPU, no cloud dependency.
