"""SQLAlchemy ORM models for the observability platform.

All primary keys are UUID strings generated at insert time.
Every model uses the SQLAlchemy 2.0 mapped_column() API with explicit
column types so schema migrations are deterministic.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


def _new_uuid() -> str:
    """Generate a new UUID4 string for use as a primary key default."""
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""


# --------------------------------------------------------------------------- #
# PipelineRun
# --------------------------------------------------------------------------- #


class PipelineRun(Base):
    """Represents a single execution of a dbt Cloud job.

    One row is written per dbt run regardless of outcome.  The ``run_id``
    field stores the dbt-assigned identifier so results can be correlated
    with the dbt Cloud UI.
    """

    __tablename__ = "pipeline_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    pipeline_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    run_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, index=True
    )  # success | failed | running | cancelled
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rows_affected: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    run_metadata: Mapped[Optional[dict]] = mapped_column(
        "metadata", JSONB, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )


# --------------------------------------------------------------------------- #
# AnomalyEvent
# --------------------------------------------------------------------------- #


class AnomalyEvent(Base):
    """Records a detected anomaly in a data pipeline or warehouse.

    Anomaly types are constrained by convention; enforcement lives in the
    service layer rather than a DB check constraint so that new types can
    be added without a migration.

    Severity levels follow standard incident taxonomy:
        P1 = critical / data-down
        P2 = high / significant impact
        P3 = medium / degraded performance
    """

    __tablename__ = "anomaly_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    pipeline_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    anomaly_type: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )  # null_spike|volume_drop|schema_drift|freshness|slow_query|cost_spike
    severity: Mapped[str] = mapped_column(
        String(4), nullable=False, index=True
    )  # P1 | P2 | P3
    description: Mapped[str] = mapped_column(Text, nullable=False)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), index=True
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    is_resolved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    anomaly_metrics: Mapped[Optional[dict]] = mapped_column(
        "metrics", JSONB, nullable=True
    )

    healing_actions: Mapped[list["HealingAction"]] = relationship(
        "HealingAction", back_populates="anomaly", cascade="all, delete-orphan"
    )


# --------------------------------------------------------------------------- #
# HealingAction
# --------------------------------------------------------------------------- #


class HealingAction(Base):
    """Records an automated or AI-recommended remediation attempt for an anomaly.

    ``success_rate`` carries a 0.0–1.0 value when the action is partially
    successful (e.g. 8/10 partitions reloaded successfully).
    """

    __tablename__ = "healing_actions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    anomaly_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("anomaly_events.id", ondelete="CASCADE"), nullable=False
    )
    action_type: Mapped[str] = mapped_column(String(64), nullable=False)
    pipeline_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="pending"
    )  # success | failed | partial | pending
    success_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    attempted_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    ai_recommendation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    anomaly: Mapped["AnomalyEvent"] = relationship(
        "AnomalyEvent", back_populates="healing_actions"
    )


# --------------------------------------------------------------------------- #
# AIInsight
# --------------------------------------------------------------------------- #


class AIInsight(Base):
    """Stores a Claude-generated proactive insight surfaced on the dashboard.

    Insights are created asynchronously by the scheduler and displayed
    to the engineer on the Overview page.
    """

    __tablename__ = "ai_insights"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(
        String(8), nullable=False, default="medium"
    )  # high | medium | low
    recommendation: Mapped[str] = mapped_column(Text, nullable=False)
    estimated_impact: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), index=True
    )


# --------------------------------------------------------------------------- #
# AlertRule
# --------------------------------------------------------------------------- #


class AlertRule(Base):
    """User-defined threshold rule that triggers a Slack alert.

    ``operator`` governs comparison direction:
        gt  - alert when metric > threshold
        lt  - alert when metric < threshold
        eq  - alert when metric == threshold
    """

    __tablename__ = "alert_rules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    metric: Mapped[str] = mapped_column(String(128), nullable=False)
    threshold: Mapped[float] = mapped_column(Float, nullable=False)
    operator: Mapped[str] = mapped_column(String(4), nullable=False)  # gt | lt | eq
    severity: Mapped[str] = mapped_column(String(4), nullable=False)  # P1 | P2 | P3
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    slack_channel: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )


# --------------------------------------------------------------------------- #
# QueryLog
# --------------------------------------------------------------------------- #


class QueryLog(Base):
    """Persists a sampled record of expensive Snowflake queries.

    ``query_text`` is capped at 2000 characters to bound row size.
    ``query_hash`` (SHA-256 hex) allows de-duplication across executions
    of the same logical query.
    """

    __tablename__ = "query_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    query_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    query_text: Mapped[str] = mapped_column(String(2000), nullable=False)
    warehouse: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    bytes_scanned: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cost_usd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    executed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, index=True
    )
    user_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
