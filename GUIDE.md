# FlowForge — Load Testing a 3rd Party System

---

## Step 1 — Map out what you're testing

Before touching the UI, write down:
- The base URL of the target (e.g. `https://api.example.com`)
- The sequence of calls that represent a real user session (login → fetch data → submit)
- Any auth tokens, API keys, or headers required
- Which endpoints you have **permission** to hammer (check their ToS/rate limit policy)

---

## Step 2 — Start your backend

```bash
cd backend
source venv/bin/activate        # Windows: venv\Scripts\activate
uvicorn main:app --reload --port 8000
```

---

## Step 3 — Build the workflow

In the UI go to **Workflows → Create Workflow**, then add steps in order:

| Step | Example | Notes |
|---|---|---|
| Auth step | `POST /auth/login` | Use **Extract Variables** → `{"token": "data.access_token"}` |
| Core action | `GET /api/users` | Add header `Authorization: Bearer {{token}}` |
| Write action | `POST /api/orders` | Body can reference `{{token}}` or any extracted var |

Set **Condition** on each step to `status == 200` so a failed auth stops the chain.

---

## Step 4 — Disable mock, set realistic load

In **Execution → Run**:
- Toggle **Use Mock API** → OFF
- Start conservative:

```
concurrency = 10    # virtual users running in parallel
iterations  = 5     # each user repeats the full workflow 5×
```

= 50 total requests. Check traces are clean before scaling.

---

## Step 5 — Scale up gradually

```
Round 1:  concurrency=10,  iterations=5    →   50 req   (baseline)
Round 2:  concurrency=25,  iterations=10   →  250 req   (normal load)
Round 3:  concurrency=50,  iterations=20   → 1000 req   (stress)
Round 4:  concurrency=100, iterations=20   → 2000 req   (peak — laptop limit)
```

Stop scaling when you see **connection errors in traces** (not 4xx/5xx from the server) — that's your laptop hitting its ceiling, not the server.

---

## Step 6 — Analyze results

Go to **Analytics → select execution**:

| Metric | What to look for |
|---|---|
| p95 / p99 response time | Should stay flat as concurrency rises — a steep jump = server degrading |
| Error rate | Any sustained >1% is worth investigating |
| Throughput (req/s) | Should scale linearly with concurrency up to the server's limit |

Go to **AI Insights → Run Anomaly Detection**:
- **Z-score** flags single spikes (e.g. one slow DB query under load)
- **IQR** flags steps that are consistently slower than the rest

---

## Step 7 — Things to watch for

| Symptom | Likely cause | Action |
|---|---|---|
| 401/403 mid-run | Auth token expired | Reduce iterations or add a re-auth step |
| 429 Too Many Requests | Rate limit hit | Back off concurrency |
| Connection reset / timeout | Server saturated or laptop fd limit | Halve concurrency — if errors disappear, it's the server |
| Response time climbing across iterations | Server not recovering between rounds | Reduce iterations or add retry delay |

---

## Laptop limits reference

| Constraint | Default | Cap |
|---|---|---|
| macOS open file descriptors | 256 | ~1000 with `ulimit -n 1000` |
| httpx connection pool | 100 connections | Set via `concurrency` in FlowForge |
| Recommended max concurrency | — | 100 |
