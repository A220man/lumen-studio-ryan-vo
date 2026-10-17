"""FastAPI dependencies shared across routers."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status

from ..core.config import settings
from ..core.database import Database, get_db

__all__ = ["get_db", "get_current_user", "CurrentUser", "require_admin"]


class CurrentUser:
    """Minimal user object — demo mode grants admin; R1 local only."""

    def __init__(self, sub: str = "demo", role: str = "admin") -> None:
        self.sub = sub
        self.role = role
        self.preferred_username = sub

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


def get_current_user(request: Request) -> CurrentUser:
    """Resolve the authenticated user.

    In demo mode (local-only, binds 127.0.0.1) all endpoints are
    accessible as ``admin``.  In production, OIDC token validation
    would run here — not yet implemented (R1 milestone).
    """
    if settings.demo_mode:
        return CurrentUser()
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required (OIDC not configured)",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_admin(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """Dependency that requires the admin role."""
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )
    return user