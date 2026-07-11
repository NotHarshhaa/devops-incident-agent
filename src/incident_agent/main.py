"""FastAPI application factory and ASGI entrypoint."""

from __future__ import annotations

from fastapi import FastAPI

from . import __version__
from .api import router
from .config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        description=(
            "An AI agent that investigates DevOps incidents across metrics, "
            "logs, Kubernetes, deployments and CI/CD, then reports a probable "
            "root cause with a recommended fix. Human approval required — "
            "nothing auto-executes."
        ),
    )
    app.include_router(router)

    @app.get("/", tags=["system"])
    def root() -> dict:
        return {
            "name": settings.app_name,
            "version": __version__,
            "docs": "/docs",
            "investigate": "POST /investigate",
        }

    return app


app = create_app()
