"""Alert evaluation and delivery service.

Evaluates user-defined AlertRules against incoming metric snapshots,
creates AnomalyEvent records in the database, and dispatches formatted
Slack messages.  Every alert delivery failure is logged but never
silently swallowed.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import httpx
import structlog
from sqlalchemy.orm import Session

from app.models.pipeline import AlertRule, AnomalyEvent

logger = structlog.get_logger(__name__)

# Severity colour codes for Slack attachment colour field.
_SEVERITY_COLOURS: dict[str, str] = {
    "P1": "#FF0000",  # red
    "P2": "#FF8C00",  # orange
    "P3": "#FFD700",  # yellow
}

_OPERATOR_FN: dict[str, Any] = {
    "gt": lambda actual, threshold: actual > threshold,
    "lt": lambda actual, threshold: actual < threshold,
    "eq": lambda actual, threshold: actual == threshold,
}


class AlertService:
    """Orchestrates alert rule evaluation, anomaly persistence, and Slack delivery.

    Args:
        slack_webhook_url: Incoming webhook URL for the target Slack workspace.
            Pass an empty string to disable Slack delivery (metrics still persisted).
        db_session: SQLAlchemy session scoped to the current request or job run.
    """

    def __init__(self, slack_webhook_url: str, db_session: Session) -> None:
        self._webhook_url = slack_webhook_url
        self._db = db_session

    # ------------------------------------------------------------------ #
    # Slack delivery
    # ------------------------------------------------------------------ #

    async def send_slack_alert(
        self,
        severity: str,
        title: str,
        description: str,
        pipeline: str | None = None,
        suggested_fix: str | None = None,
    ) -> None:
        """Post a formatted alert message to Slack.

        Uses the Slack attachment API so severity is communicated via
        colour coding.  Does nothing if no webhook URL is configured.

        Args:
            severity: P1, P2, or P3.
            title: Short alert title shown in bold.
            description: Longer body text explaining the alert.
            pipeline: Optional pipeline name for context.
            suggested_fix: Optional AI-recommended fix string.

        Raises:
            httpx.HTTPError: Re-raised after logging so callers can handle.
        """
        if not self._webhook_url:
            logger.warning("alert.slack.no_webhook_configured")
            return

        colour = _SEVERITY_COLOURS.get(severity, "#808080")
        fields = [
            {"title": "Severity", "value": severity, "short": True},
        ]
        if pipeline:
            fields.append({"title": "Pipeline", "value": pipeline, "short": True})
        if suggested_fix:
            fields.append({"title": "Suggested Fix", "value": suggested_fix, "short": False})

        payload = {
            "attachments": [
                {
                    "color": colour,
                    "title": f"[{severity}] {title}",
                    "text": description,
                    "fields": fields,
                    "footer": "Data Engineering Observability Platform",
                    "ts": int(datetime.now(timezone.utc).timestamp()),
                }
            ]
        }

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    self._webhook_url,
                    content=json.dumps(payload),
                    headers={"Content-Type": "application/json"},
                )
                response.raise_for_status()
            logger.info("alert.slack.sent", severity=severity, title=title)
        except httpx.HTTPError as exc:
            logger.error("alert.slack.send_failed", error=str(exc), title=title)
            raise

    # ------------------------------------------------------------------ #
    # Rule evaluation
    # ------------------------------------------------------------------ #

    async def evaluate_alert_rules(self, metrics: dict) -> list[dict]:
        """Compare a metrics snapshot against all active AlertRules.

        Args:
            metrics: Dict mapping metric names to their current numeric values.
                Example: {"failed_pipeline_count": 3, "avg_query_ms": 12000}

        Returns:
            List of dicts describing each triggered rule with keys:
            rule_id, rule_name, metric, actual_value, threshold, severity.
        """
        triggered: list[dict] = []
        active_rules: list[AlertRule] = (
            self._db.query(AlertRule).filter(AlertRule.is_active.is_(True)).all()
        )

        for rule in active_rules:
            actual = metrics.get(rule.metric)
            if actual is None:
                continue

            compare = _OPERATOR_FN.get(rule.operator)
            if compare is None:
                logger.warning("alert.unknown_operator", operator=rule.operator)
                continue

            if compare(actual, rule.threshold):
                triggered.append(
                    {
                        "rule_id": rule.id,
                        "rule_name": rule.name,
                        "metric": rule.metric,
                        "actual_value": actual,
                        "threshold": rule.threshold,
                        "severity": rule.severity,
                        "slack_channel": rule.slack_channel,
                    }
                )
                logger.info(
                    "alert.rule_triggered",
                    rule=rule.name,
                    metric=rule.metric,
                    actual=actual,
                    threshold=rule.threshold,
                )

        return triggered

    # ------------------------------------------------------------------ #
    # Anomaly lifecycle
    # ------------------------------------------------------------------ #

    async def create_anomaly(
        self,
        pipeline_name: str,
        anomaly_type: str,
        severity: str,
        description: str,
        metrics: dict,
    ) -> AnomalyEvent:
        """Persist a new anomaly record to the database.

        Args:
            pipeline_name: Name of the affected pipeline.
            anomaly_type: One of: null_spike, volume_drop, schema_drift,
                freshness, slow_query, cost_spike.
            severity: P1, P2, or P3.
            description: Human-readable description of the anomaly.
            metrics: Supporting metric snapshot as a JSON-serialisable dict.

        Returns:
            The newly created and committed AnomalyEvent instance.
        """
        anomaly = AnomalyEvent(
            pipeline_name=pipeline_name,
            anomaly_type=anomaly_type,
            severity=severity,
            description=description,
            anomaly_metrics=metrics,
            is_resolved=False,
            detected_at=datetime.now(timezone.utc),
        )
        self._db.add(anomaly)
        self._db.commit()
        self._db.refresh(anomaly)
        logger.info(
            "alert.anomaly_created",
            anomaly_id=anomaly.id,
            pipeline=pipeline_name,
            type=anomaly_type,
            severity=severity,
        )
        return anomaly

    async def resolve_anomaly(self, anomaly_id: str) -> None:
        """Mark an anomaly as resolved.

        Args:
            anomaly_id: UUID of the AnomalyEvent to resolve.

        Raises:
            ValueError: If the anomaly_id does not exist in the database.
        """
        anomaly: AnomalyEvent | None = (
            self._db.query(AnomalyEvent).filter(AnomalyEvent.id == anomaly_id).first()
        )
        if anomaly is None:
            raise ValueError(f"AnomalyEvent {anomaly_id!r} not found.")

        anomaly.is_resolved = True
        anomaly.resolved_at = datetime.now(timezone.utc)
        self._db.commit()
        logger.info("alert.anomaly_resolved", anomaly_id=anomaly_id)
