"""FastAPI route handlers for the observability platform.

All routes follow a consistent pattern:
  1. Validate input via Pydantic models.
  2. Delegate to a service class.
  3. Return a typed Pydantic response model.
  4. Catch exceptions at the route boundary and return appropriate HTTP codes.

External service calls (dbt Cloud, Snowflake, Claude) are never allowed to
propagate unhandled exceptions to the caller.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session
from starlette.responses import Response

from app.core.config import settings
from app.core.database import get_db
from app.models.pipeline import AIInsight, AnomalyEvent, PipelineRun
from app.services.alert_service import AlertService
from app.services.claude_service import ClaudeService
from app.services.dbt_service import DbtCloudService
from app.services.snowflake_service import SnowflakeService

logger = structlog.get_logger(__name__)
router = APIRouter()


# --------------------------------------------------------------------------- #
# Dependency factories
# --------------------------------------------------------------------------- #


def get_dbt_service() -> DbtCloudService:
    """Instantiate the dbt Cloud service using settings."""
    return DbtCloudService(
        api_token=settings.DBT_CLOUD_API_TOKEN,
        account_id=settings.DBT_CLOUD_ACCOUNT_ID,
    )


def get_snowflake_service() -> SnowflakeService:
    """Instantiate the Snowflake service using settings."""
    return SnowflakeService(
        account=settings.SNOWFLAKE_ACCOUNT,
        user=settings.SNOWFLAKE_USER,
        password=settings.SNOWFLAKE_PASSWORD,
        database=settings.SNOWFLAKE_DATABASE,
        warehouse=settings.SNOWFLAKE_WAREHOUSE,
        role=settings.SNOWFLAKE_ROLE,
    )


def get_claude_service() -> ClaudeService:
    """Instantiate the Claude AI co-pilot service using settings."""
    return ClaudeService(api_key=settings.ANTHROPIC_API_KEY)


# --------------------------------------------------------------------------- #
# Pydantic request / response models
# --------------------------------------------------------------------------- #


class HealthResponse(BaseModel):
    """Liveness probe response schema."""

    status: str
    timestamp: datetime
    version: str


class DashboardOverviewResponse(BaseModel):
    """Aggregated KPI snapshot for the dashboard overview card."""

    total_pipelines: int
    healthy_pipelines: int
    failed_today: int
    anomalies_active: int
    avg_success_rate_pct: float
    total_cost_today_usd: float


class AnomalyResponse(BaseModel):
    """Single anomaly event returned from the list endpoint."""

    id: str
    pipeline_name: str
    anomaly_type: str
    severity: str
    description: str
    detected_at: datetime
    resolved_at: Optional[datetime]
    is_resolved: bool
    metrics: Optional[dict]


class AIInsightResponse(BaseModel):
    """Single AI insight returned from the insights endpoint."""

    id: str
    title: str
    description: str
    priority: str
    recommendation: str
    estimated_impact: Optional[str]
    created_at: datetime


class AnalyzeQueryRequest(BaseModel):
    """Request body for the /snowflake/analyze-query endpoint."""

    query_text: str
    warehouse: str
    duration_ms: int
    bytes_scanned: int


# --------------------------------------------------------------------------- #
# Health
# --------------------------------------------------------------------------- #


@router.get("/health", response_model=HealthResponse, tags=["health"])
async def health_check() -> HealthResponse:
    """Lightweight liveness probe.

    Returns:
        HealthResponse with status=healthy and current UTC timestamp.
    """
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(timezone.utc),
        version="1.0.0",
    )


# --------------------------------------------------------------------------- #
# Dashboard
# --------------------------------------------------------------------------- #


@router.get(
    "/dashboard/overview",
    response_model=DashboardOverviewResponse,
    tags=["dashboard"],
)
async def get_dashboard_overview(
    db: Session = Depends(get_db),
) -> DashboardOverviewResponse:
    """Aggregate key health metrics for the main dashboard overview card.

    Queries the local database only; does not call external services so the
    response stays fast.

    Args:
        db: Database session injected by FastAPI.

    Returns:
        DashboardOverviewResponse with aggregated pipeline and anomaly stats.
    """
    try:
        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        total_pipelines = (
            db.query(func.count(func.distinct(PipelineRun.pipeline_name))).scalar() or 0
        )
        healthy_pipelines = (
            db.query(func.count(func.distinct(PipelineRun.pipeline_name)))
            .filter(
                PipelineRun.status == "success",
                PipelineRun.completed_at >= today_start - timedelta(days=1),
            )
            .scalar()
            or 0
        )
        failed_today = (
            db.query(func.count(PipelineRun.id))
            .filter(
                PipelineRun.status == "failed",
                PipelineRun.started_at >= today_start,
            )
            .scalar()
            or 0
        )
        anomalies_active = (
            db.query(func.count(AnomalyEvent.id))
            .filter(AnomalyEvent.is_resolved.is_(False))
            .scalar()
            or 0
        )

        recent_runs = (
            db.query(PipelineRun)
            .filter(PipelineRun.completed_at >= today_start - timedelta(days=7))
            .all()
        )
        success_count = sum(1 for r in recent_runs if r.status == "success")
        avg_success_rate = round(
            success_count / max(len(recent_runs), 1) * 100, 1
        )

        return DashboardOverviewResponse(
            total_pipelines=total_pipelines,
            healthy_pipelines=healthy_pipelines,
            failed_today=failed_today,
            anomalies_active=anomalies_active,
            avg_success_rate_pct=avg_success_rate,
            total_cost_today_usd=0.0,
        )
    except Exception as exc:
        logger.error("routes.dashboard_overview.failed", error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to fetch dashboard overview.")


# --------------------------------------------------------------------------- #
# dbt Cloud
# --------------------------------------------------------------------------- #


@router.get("/dbt/runs", tags=["dbt"])
async def get_dbt_runs(
    limit: int = Query(default=20, ge=1, le=100),
    status: Optional[str] = Query(default=None),
    dbt: DbtCloudService = Depends(get_dbt_service),
) -> List[dict]:
    """Fetch recent dbt Cloud job runs.

    Args:
        limit: Number of runs to return (1-100, default 20).
        status: Optional dbt status filter.

    Returns:
        List of run dicts from the dbt Cloud API.
    """
    try:
        return await dbt.get_runs(limit=limit, status=status)
    except Exception as exc:
        logger.error("routes.dbt_runs.failed", error=str(exc))
        raise HTTPException(status_code=502, detail="Failed to fetch dbt runs.")


@router.get("/dbt/failures", tags=["dbt"])
async def get_dbt_failures(
    dbt: DbtCloudService = Depends(get_dbt_service),
) -> List[dict]:
    """Return the most recent failed dbt test results across recent runs.

    Fetches the last 10 runs, identifies error-status runs, and returns parsed
    test failure records.  Use POST /dbt/analyze/{run_id} for AI diagnosis.

    Returns:
        List of test failure dicts with model, test_name, severity, message.
    """
    try:
        runs = await dbt.get_runs(limit=10)
        failed_runs = [r for r in runs if r.get("status") == 20]  # 20 = Error

        all_failures: list[dict] = []
        tasks = [dbt.get_run_results(r["id"]) for r in failed_runs[:5]]
        results_list = await asyncio.gather(*tasks, return_exceptions=True)

        for run, result in zip(failed_runs[:5], results_list):
            if isinstance(result, Exception):
                logger.warning(
                    "routes.dbt_failures.run_skip", run_id=run.get("id")
                )
                continue
            parsed = dbt.parse_test_failures(result)
            for f in parsed:
                f["run_id"] = run.get("id")
            all_failures.extend(parsed)

        return all_failures
    except Exception as exc:
        logger.error("routes.dbt_failures.failed", error=str(exc))
        raise HTTPException(status_code=502, detail="Failed to fetch dbt failures.")


@router.post("/dbt/analyze/{run_id}", tags=["dbt"])
async def analyze_dbt_run(
    run_id: int,
    dbt: DbtCloudService = Depends(get_dbt_service),
    claude: ClaudeService = Depends(get_claude_service),
    db: Session = Depends(get_db),
) -> dict:
    """Fetch test failures for a specific run and return AI analysis.

    Persists a new AIInsight record for each analysed failure so the result
    is visible on the insights endpoint without re-calling Claude.

    Args:
        run_id: dbt Cloud numeric run identifier.

    Returns:
        Dict with keys: run_id, failures (list), analysis (dict from Claude).
    """
    try:
        run_results = await dbt.get_run_results(run_id)
        failures = dbt.parse_test_failures(run_results)

        if not failures:
            return {"run_id": run_id, "failures": [], "analysis": {}}

        first = failures[0]
        analysis = await claude.analyze_dbt_failure(
            test_name=first.get("test_name", "unknown"),
            model_name=first.get("model", "unknown"),
            error_message=first.get("message", ""),
        )

        if "error" not in analysis:
            insight = AIInsight(
                title=f"dbt failure: {first.get('test_name', 'unknown')} on {first.get('model', 'unknown')}",
                description=analysis.get("root_cause", ""),
                priority="high" if analysis.get("severity") == "P1" else "medium",
                recommendation=analysis.get("fix_sql") or "; ".join(
                    analysis.get("prevention_steps", [])
                ),
                estimated_impact="Prevents future data quality failures in this model",
            )
            db.add(insight)
            db.commit()

        return {"run_id": run_id, "failures": failures, "analysis": analysis}
    except Exception as exc:
        logger.error("routes.dbt_analyze.failed", run_id=run_id, error=str(exc))
        raise HTTPException(status_code=502, detail="Failed to analyze dbt run.")


# --------------------------------------------------------------------------- #
# Snowflake
# --------------------------------------------------------------------------- #


@router.get("/snowflake/slow-queries", tags=["snowflake"])
async def get_slow_queries(
    hours: int = Query(default=24, ge=1, le=168),
    min_duration_ms: int = Query(default=5000, ge=100),
    sf: SnowflakeService = Depends(get_snowflake_service),
) -> List[dict]:
    """Return Snowflake queries exceeding the execution time threshold.

    Args:
        hours: Lookback window in hours (1-168, default 24).
        min_duration_ms: Minimum execution time filter in ms (default 5000).

    Returns:
        List of slow query dicts from ACCOUNT_USAGE.QUERY_HISTORY.
    """
    try:
        return sf.get_slow_queries(min_duration_ms=min_duration_ms, hours=hours)
    except Exception as exc:
        logger.error("routes.slow_queries.failed", error=str(exc))
        raise HTTPException(status_code=502, detail="Failed to fetch slow queries.")


@router.get("/snowflake/costs", tags=["snowflake"])
async def get_warehouse_costs(
    days: int = Query(default=30, ge=1, le=90),
    sf: SnowflakeService = Depends(get_snowflake_service),
) -> List[dict]:
    """Return daily Snowflake credit consumption per warehouse.

    Args:
        days: Lookback window in days (1-90, default 30).

    Returns:
        List of dicts with warehouse_name, usage_date, credits_used.
    """
    try:
        return sf.get_warehouse_costs(days=days)
    except Exception as exc:
        logger.error("routes.warehouse_costs.failed", error=str(exc))
        raise HTTPException(status_code=502, detail="Failed to fetch warehouse costs.")


@router.get("/snowflake/freshness", tags=["snowflake"])
async def get_table_freshness(
    schema: str = Query(default="PUBLIC"),
    sf: SnowflakeService = Depends(get_snowflake_service),
) -> List[dict]:
    """Return freshness status for all tables in the configured schema.

    Args:
        schema: Snowflake schema name (default PUBLIC).

    Returns:
        List of dicts with table_name, last_altered, hours_since_update, is_stale.
    """
    try:
        return sf.get_table_freshness(
            database=settings.SNOWFLAKE_DATABASE,
            schema=schema,
        )
    except Exception as exc:
        logger.error("routes.table_freshness.failed", error=str(exc))
        raise HTTPException(status_code=502, detail="Failed to fetch table freshness.")


@router.post("/snowflake/analyze-query", tags=["snowflake"])
async def analyze_query(
    body: AnalyzeQueryRequest,
    claude: ClaudeService = Depends(get_claude_service),
    db: Session = Depends(get_db),
) -> dict:
    """Send a slow query to Claude for root-cause analysis.

    Persists the resulting analysis as an AIInsight for later retrieval.

    Args:
        body: AnalyzeQueryRequest with query_text, warehouse, duration_ms,
            bytes_scanned.

    Returns:
        Claude analysis dict with analysis, suggestions, priority,
        estimated_improvement.
    """
    try:
        analysis = await claude.analyze_slow_query(
            query_text=body.query_text,
            warehouse=body.warehouse,
            duration_ms=body.duration_ms,
            bytes_scanned=body.bytes_scanned,
        )

        if "error" not in analysis:
            insight = AIInsight(
                title=f"Slow query on {body.warehouse} ({body.duration_ms} ms)",
                description=analysis.get("analysis", ""),
                priority=analysis.get("priority", "medium"),
                recommendation="\n".join(analysis.get("suggestions", [])),
                estimated_impact=analysis.get("estimated_improvement", ""),
            )
            db.add(insight)
            db.commit()

        return analysis
    except Exception as exc:
        logger.error("routes.analyze_query.failed", error=str(exc))
        raise HTTPException(status_code=502, detail="Failed to analyze query.")


# --------------------------------------------------------------------------- #
# Anomalies
# --------------------------------------------------------------------------- #


@router.get("/anomalies", tags=["anomalies"])
async def list_anomalies(
    days: int = Query(default=7, ge=1, le=90),
    severity: Optional[str] = Query(default=None),
    resolved: bool = Query(default=False),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> List[dict]:
    """List anomaly events from the database.

    Args:
        days: Lookback window in days (1-90, default 7).
        severity: Optional severity filter (P1, P2, P3).
        resolved: Include resolved anomalies when True (default False).
        limit: Maximum records to return (default 100).

    Returns:
        List of anomaly dicts ordered by detected_at descending.
    """
    try:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        query = db.query(AnomalyEvent).filter(AnomalyEvent.detected_at >= since)

        if not resolved:
            query = query.filter(AnomalyEvent.is_resolved.is_(False))
        if severity:
            query = query.filter(AnomalyEvent.severity == severity.upper())

        anomalies = (
            query.order_by(AnomalyEvent.detected_at.desc()).limit(limit).all()
        )

        return [
            {
                "id": a.id,
                "pipeline_name": a.pipeline_name,
                "anomaly_type": a.anomaly_type,
                "severity": a.severity,
                "description": a.description,
                "detected_at": a.detected_at.isoformat() if a.detected_at else None,
                "resolved_at": a.resolved_at.isoformat() if a.resolved_at else None,
                "is_resolved": a.is_resolved,
                "metrics": a.anomaly_metrics,
            }
            for a in anomalies
        ]
    except Exception as exc:
        logger.error("routes.list_anomalies.failed", error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to fetch anomalies.")


@router.post("/anomalies/{anomaly_id}/resolve", tags=["anomalies"])
async def resolve_anomaly(
    anomaly_id: str,
    db: Session = Depends(get_db),
) -> dict:
    """Mark an anomaly as resolved.

    Args:
        anomaly_id: UUID of the anomaly to resolve.

    Returns:
        Confirmation dict with anomaly_id and resolved_at timestamp.

    Raises:
        HTTPException 404: If the anomaly does not exist.
    """
    alert_service = AlertService(
        slack_webhook_url=settings.SLACK_WEBHOOK_URL,
        db_session=db,
    )
    try:
        await alert_service.resolve_anomaly(anomaly_id)
        return {
            "anomaly_id": anomaly_id,
            "resolved_at": datetime.now(timezone.utc).isoformat(),
        }
    except ValueError:
        raise HTTPException(
            status_code=404, detail=f"Anomaly {anomaly_id!r} not found."
        )
    except Exception as exc:
        logger.error(
            "routes.resolve_anomaly.failed", anomaly_id=anomaly_id, error=str(exc)
        )
        raise HTTPException(status_code=500, detail="Failed to resolve anomaly.")


# --------------------------------------------------------------------------- #
# AI Insights
# --------------------------------------------------------------------------- #


@router.get("/insights", tags=["insights"])
async def list_insights(
    priority: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
) -> List[dict]:
    """Return the 20 most recent AI-generated insights.

    Args:
        priority: Optional filter by priority (high, medium, low).
        db: Database session.

    Returns:
        List of insight dicts ordered by created_at descending.
    """
    try:
        query = db.query(AIInsight)
        if priority:
            query = query.filter(AIInsight.priority == priority.lower())

        insights = query.order_by(AIInsight.created_at.desc()).limit(20).all()

        return [
            {
                "id": i.id,
                "title": i.title,
                "description": i.description,
                "priority": i.priority,
                "recommendation": i.recommendation,
                "estimated_impact": i.estimated_impact,
                "created_at": i.created_at.isoformat() if i.created_at else None,
            }
            for i in insights
        ]
    except Exception as exc:
        logger.error("routes.list_insights.failed", error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to fetch insights.")


# --------------------------------------------------------------------------- #
# Prometheus metrics
# --------------------------------------------------------------------------- #


@router.get("/metrics", tags=["observability"], include_in_schema=False)
async def prometheus_metrics() -> Response:
    """Expose Prometheus-format metrics for scraping.

    Returns:
        Plain-text Prometheus metrics payload.
    """
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
