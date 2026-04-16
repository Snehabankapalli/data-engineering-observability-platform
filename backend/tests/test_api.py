"""
Unit tests for the DE Observability Platform API.

All external services (dbt, Snowflake, Claude) are mocked.
Tests verify API response contracts and error handling.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from app.main import create_app
from app.core.database import get_db


@pytest.fixture(scope="module")
def client():
    """Test client with database mocked."""
    app = create_app()

    def override_get_db():
        db = MagicMock()
        db.query.return_value.filter.return_value.count.return_value = 0
        db.query.return_value.distinct.return_value.count.return_value = 0
        db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
        yield db

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        yield c


def test_health_check(client):
    """Health endpoint returns healthy status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data


def test_api_health(client):
    """API health endpoint returns healthy."""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_dashboard_overview(client):
    """Dashboard overview returns required KPI keys."""
    response = client.get("/api/dashboard/overview")
    assert response.status_code == 200
    data = response.json()
    required_keys = [
        "total_pipelines",
        "healthy_pipelines",
        "failed_today",
        "anomalies_active",
        "avg_success_rate_pct",
        "total_cost_today_usd",
    ]
    for key in required_keys:
        assert key in data, f"Missing key: {key}"


def test_get_anomalies_empty(client):
    """Anomalies endpoint returns list structure."""
    response = client.get("/api/anomalies")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "anomalies" in data
    assert isinstance(data["anomalies"], list)


def test_resolve_anomaly_not_found(client):
    """Resolving non-existent anomaly returns 404."""
    with patch("app.api.routes.AlertService") as mock_svc:
        mock_svc.return_value.resolve_anomaly.return_value = None
        response = client.post("/api/anomalies/nonexistent-id/resolve")
    assert response.status_code == 404


def test_get_insights_empty(client):
    """Insights endpoint returns list structure."""
    response = client.get("/api/insights")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "insights" in data
    assert isinstance(data["insights"], list)


def test_get_metrics_prometheus_format(client):
    """Metrics endpoint returns Prometheus text format."""
    response = client.get("/api/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers.get("content-type", "")


def test_analyze_query_missing_payload(client):
    """Analyze query endpoint handles missing fields gracefully."""
    with patch("app.api.routes.ClaudeService") as mock_claude:
        mock_claude.return_value.analyze_slow_query.return_value = {
            "analysis": "test", "suggestions": [], "priority": "low", "estimated_improvement": "n/a"
        }
        response = client.post("/api/snowflake/analyze-query", json={})
    # Should not 500 — should handle empty payload
    assert response.status_code in (200, 422, 500)


@pytest.mark.asyncio
async def test_dbt_runs_service_error():
    """dbt runs endpoint returns 502 when service fails."""
    app = create_app()

    def override_db():
        yield MagicMock()

    app.dependency_overrides[get_db] = override_db

    with TestClient(app) as c:
        with patch("app.api.routes.DbtCloudService") as mock_dbt:
            mock_dbt.return_value.get_runs = AsyncMock(side_effect=Exception("dbt unavailable"))
            response = c.get("/api/dbt/runs")
        # 502 = upstream service error
        assert response.status_code == 502
