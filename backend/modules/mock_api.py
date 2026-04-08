import json
import random
import time
from sqlmodel import Session, select
from db import MockApiConfig, engine
from typing import Optional


# ─── Built-in mock routes (fallback if no DB config) ──────────────────────────

BUILTIN_MOCKS = {
    ("GET", "/mock/health"): {
        "status_code": 200,
        "body": {"status": "ok", "service": "mock-api"},
        "latency_range": (10, 50),
    },
    ("POST", "/mock/login"): {
        "status_code": 200,
        "body": {"token": "mock-jwt-token-abc123", "user_id": "user_001", "role": "admin"},
        "latency_range": (20, 80),
    },
    ("GET", "/mock/users"): {
        "status_code": 200,
        "body": {"users": [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}], "total": 2},
        "latency_range": (15, 60),
    },
    ("POST", "/mock/data"): {
        "status_code": 201,
        "body": {"id": "data_001", "created": True, "message": "Data created successfully"},
        "latency_range": (30, 100),
    },
    ("GET", "/mock/items"): {
        "status_code": 200,
        "body": {"items": [{"id": 1, "name": "Item A", "price": 9.99}], "count": 1},
        "latency_range": (10, 40),
    },
    ("DELETE", "/mock/item"): {
        "status_code": 200,
        "body": {"deleted": True, "message": "Item deleted"},
        "latency_range": (10, 30),
    },
    ("PUT", "/mock/update"): {
        "status_code": 200,
        "body": {"updated": True, "id": "item_001"},
        "latency_range": (20, 70),
    },
}


def get_mock_response(endpoint: str, method: str) -> dict:
    """Return a mock response for an endpoint. Checks DB first, then builtins."""
    method = method.upper()

    # Normalize endpoint for matching
    path = endpoint.replace("http://localhost:8000", "").replace("http://127.0.0.1:8000", "")

    # Try DB config
    with Session(engine) as session:
        config = session.exec(
            select(MockApiConfig).where(
                MockApiConfig.endpoint == path,
                MockApiConfig.http_method == method,
            )
        ).first()

        if config:
            latency = random.randint(config.latency_min, config.latency_max)
            should_fail = random.random() < config.error_rate
            if should_fail:
                return {
                    "status_code": 500,
                    "body": {"error": "Simulated failure", "endpoint": path},
                    "latency": latency,
                }
            try:
                body = json.loads(config.response_template)
            except Exception:
                body = {"response": config.response_template}
            return {
                "status_code": config.status_code,
                "body": body,
                "latency": latency,
            }

    # Try builtins
    key = (method, path)
    if key in BUILTIN_MOCKS:
        mock = BUILTIN_MOCKS[key]
        lo, hi = mock["latency_range"]
        return {
            "status_code": mock["status_code"],
            "body": mock["body"],
            "latency": random.randint(lo, hi),
        }

    # Default 404
    return {
        "status_code": 404,
        "body": {"error": f"No mock configured for {method} {path}"},
        "latency": 10,
    }


# ─── Mock config CRUD ──────────────────────────────────────────────────────────

def create_mock_config(
    session: Session,
    endpoint: str,
    http_method: str,
    response_template: dict,
    latency_min: int = 0,
    latency_max: int = 100,
    error_rate: float = 0.0,
    status_code: int = 200,
) -> MockApiConfig:
    config = MockApiConfig(
        endpoint=endpoint,
        http_method=http_method.upper(),
        response_template=json.dumps(response_template),
        latency_min=latency_min,
        latency_max=latency_max,
        error_rate=error_rate,
        status_code=status_code,
    )
    session.add(config)
    session.commit()
    session.refresh(config)
    return config


def list_mock_configs(session: Session):
    return list(session.exec(select(MockApiConfig)).all())


def delete_mock_config(session: Session, mock_id: str) -> bool:
    config = session.exec(select(MockApiConfig).where(MockApiConfig.mock_id == mock_id)).first()
    if not config:
        return False
    session.delete(config)
    session.commit()
    return True
