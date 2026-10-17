"""Health-check and version info endpoints (no auth required)."""

from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter(prefix="/api/v1", tags=["health"])


@router.get("/health", tags=["health"])
def health() -> dict:
    """Simple liveness probe."""
    return {"status": "ok", "service": "lumen-studio"}


@router.get("/version", response_model=dict, tags=["meta"])
def version(request: Request) -> dict:
    """Return version and runtime configuration (no secrets)."""
    s = request.app.state.settings
    return {
        "version": s.version,
        "env": s.app_env,
        "demo_mode": s.demo_mode,
    }