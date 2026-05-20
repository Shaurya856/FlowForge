from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db import init_db
from modules.execution_engine import close_shared_client
from routers import dashboard, executions, mock, workflows

app = FastAPI(title="API Workflow Platform", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(workflows.router)
app.include_router(executions.router)
app.include_router(mock.router)
app.include_router(dashboard.router)


@app.on_event("startup")
def on_startup():
    init_db()


@app.on_event("shutdown")
async def on_shutdown():
    await close_shared_client()
