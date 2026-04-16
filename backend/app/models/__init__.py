"""SQLAlchemy model registry.

Importing this package exposes all ORM models so that Alembic autogenerate
and create_tables() can discover them via the shared Base metadata.
"""

from app.models.pipeline import (  # noqa: F401
    AnomalyEvent,
    AIInsight,
    AlertRule,
    HealingAction,
    PipelineRun,
    QueryLog,
)
