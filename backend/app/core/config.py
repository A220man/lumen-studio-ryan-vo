"""Application settings loaded from environment variables.

Demo mode binds to localhost and disables authentication.  In production
(``APP_ENV=production``) demo mode is refused at startup — the operator
must run with ``DEMO_MODE=false`` and configure Keycloak OIDC.
"""

from __future__ import annotations

import os
from pathlib import Path

_BASE_DIR = Path(__file__).resolve().parent.parent.parent


def _read_version() -> str:
    """Read product version from the root VERSION file, never hardcode."""
    candidates = [
        _BASE_DIR / "VERSION",
        _BASE_DIR.parent / "VERSION",
        Path(os.getenv("VERSION_FILE", "")),
    ]
    for p in candidates:
        if p and p.is_file():
            return p.read_text().strip() or "0.0.0"
    return "0.0.0"


class Settings:
    """Env-driven configuration.  Plain class (no extra deps)."""

    # --- Runtime ---
    app_env: str = os.getenv("APP_ENV", "development")

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    # --- Server binding ---
    app_host: str = os.getenv("APP_HOST", "127.0.0.1")
    app_port: int = int(os.getenv("APP_PORT", "8000"))

    # --- Demo mode ---
    @property
    def demo_mode(self) -> bool:
        raw = os.getenv("DEMO_MODE", "")
        if raw:
            return raw.lower() == "true"
        # Default: demo on in dev, off in production
        return not self.is_production

    # --- Database ---
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./lumen.db")

    # --- Keycloak OIDC (planned R2) ---
    keycloak_url: str | None = os.getenv("KEYCLOAK_URL") or None
    keycloak_realm: str | None = os.getenv("KEYCLOAK_REALM") or None
    keycloak_client_id: str | None = os.getenv("KEYCLOAK_CLIENT_ID") or None
    keycloak_client_secret: str | None = os.getenv("KEYCLOAK_CLIENT_SECRET") or None
    oidc_audience: str | None = os.getenv("OIDC_AUDIENCE") or None

    # --- LLM adapter (opt-in; R1 returns advisory-unavailable) ---
    llm_api_key: str | None = os.getenv("LLM_API_KEY") or None
    llm_provider: str = os.getenv("LLM_PROVIDER", "openai-compatible")
    llm_model: str | None = os.getenv("LLM_MODEL") or None
    llm_base_url: str | None = os.getenv("LLM_BASE_URL") or None

    # --- Version ---
    version: str = _read_version()

    def __init__(self) -> None:
        self._lock_demo = False

    def validate_startup(self) -> None:
        """Refuse demo mode in production."""
        if self.demo_mode and self.is_production:
            raise RuntimeError(
                "DEMO_MODE=true is refused when APP_ENV=production. "
                "Set DEMO_MODE=false and configure Keycloak OIDC."
            )

    def redact(self) -> dict:
        """Return a safe summary for diagnostics (no secrets)."""
        return {
            "env": self.app_env,
            "demo_mode": self.demo_mode,
            "database_url": "[redacted]" if "://" in self.database_url else self.database_url,
            "version": self.version,
        }


settings = Settings()