from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from db import get_session
from modules.mock_api import create_mock_config, delete_mock_config, list_mock_configs
from routers.schemas import MockConfigCreate

router = APIRouter()


@router.get("/mock-configs")
def list_mocks(session: Session = Depends(get_session)):
    return list_mock_configs(session)


@router.post("/mock-configs", status_code=201)
def create_mock(body: MockConfigCreate, session: Session = Depends(get_session)):
    return create_mock_config(
        session, body.endpoint, body.http_method, body.response_template,
        body.latency_min, body.latency_max, body.error_rate, body.status_code,
    )


@router.delete("/mock-configs/{mock_id}")
def delete_mock(mock_id: str, session: Session = Depends(get_session)):
    if not delete_mock_config(session, mock_id):
        raise HTTPException(404, "Mock config not found")
    return {"deleted": True}
