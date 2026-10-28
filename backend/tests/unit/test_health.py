from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient


def test_health_live_ok(client: TestClient) -> None:
    for path in ("/api/v1/health", "/api/v1/health/live"):
        response = client.get(path)
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


def test_health_ready_ok_when_db_connects(client: TestClient) -> None:
    mock_conn = MagicMock()
    mock_cm = MagicMock()
    mock_cm.__enter__.return_value = mock_conn
    mock_cm.__exit__.return_value = None

    with patch("src.api.v1.health.engine") as mock_engine:
        mock_engine.connect.return_value = mock_cm
        response = client.get("/api/v1/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    mock_conn.execute.assert_called_once()


def test_health_ready_503_when_db_fails(client: TestClient) -> None:
    with patch("src.api.v1.health.engine") as mock_engine:
        mock_engine.connect.side_effect = OSError("connection refused")
        response = client.get("/api/v1/health/ready")

    assert response.status_code == 503
    assert response.json()["detail"] == "not ready"
    assert "postgresql" not in response.text.lower()
    assert "5432" not in response.text


def test_sentry_debug_raises_in_non_production(client: TestClient) -> None:
    with pytest.raises(Exception, match="Sanity test error"):
        client.get("/sentry-debug")


@pytest.mark.asyncio
async def test_sentry_debug_hidden_in_production() -> None:
    from src.main import trigger_error

    with patch("src.main.settings") as mock_settings:
        mock_settings.allow_sentry_debug = False
        with pytest.raises(HTTPException) as exc_info:
            await trigger_error()
    assert exc_info.value.status_code == 404


def test_app_imports() -> None:
    from src.main import app as imported_app

    assert imported_app.title
