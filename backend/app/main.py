"""
Data Engineering Observability Platform — FastAPI application entry point.
"""

import logging
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.api.routes import router
from app.core.config import get_settings
from app.core.database import create_tables

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),
    ]
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    settings = get_settings()
    logger.info("Starting DE Observability Platform v1.0.0")
    logger.info("Debug mode: %s", settings.DEBUG)
    create_tables()
    logger.info("Database tables ready")
    yield
    logger.info("Platform shutting down")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Data Engineering Observability Platform",
        description="Production monitoring for dbt + Snowflake with Claude AI co-pilot",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router, prefix="/api")

    @app.get("/", include_in_schema=False)
    def root():
        return RedirectResponse(url="/docs")

    @app.get("/health", include_in_schema=False)
    def health():
        return {"status": "healthy", "version": "1.0.0"}

    return app


app = create_app()
