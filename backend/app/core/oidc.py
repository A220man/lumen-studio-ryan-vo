"""OIDC helper utilities for Lumen Studio."""

from __future__ import annotations

import base64
import hashlib
import json
import secrets
import time
from typing import Any

from .config import settings
from .jwt import create_session_token, verify_session_token


class OIDCFlow:
    """Manage OIDC authorization code flow with PKCE and mock token exchange."""

    def __init__(self) -> None:
        # In‑memory state store; keyed by random identifier for demo
        self._states: dict[str, float] = {}
        self._code_verifiers: dict[str, float] = {}

    def generate_state(self) -> str:
        """Return a random state string."""
        state = secrets.token_urlsafe(32)
        self._states[state] = time.time()
        return state

    def verify_state(self, state: str | None) -> bool:
        """Validate state against stored value (expire after 10 min)."""
        if not state or state not in self._states:
            return False
        if time.time() - self._states[state] > 600:
            del self._states[state]
            return False
        return True

    def generate_pkce(self) -> tuple[str, str]:
        """Generate PKCE code verifier and code challenge (S256)."""
        verifier = secrets.token_urlsafe(48)
        sha256 = hashlib.sha256(verifier.encode()).digest()
        challenge = base64.urlsafe_b64encode(sha256).rstrip(b"=").decode()
        self._code_verifiers[verifier] = time.time()
        return verifier, challenge

    def exchange_code_for_tokens(
        self,
        code: str,
        code_verifier: str,
        redirect_uri: str,
    ) -> dict[str, Any]:
        """Mock token exchange – returns a fake JWT with user info."""
        # Real flow would POST to Keycloak, but here we just simulate success.
        # Validate verifier (optional)
        if not self._code_verifiers.pop(code_verifier, None):
            raise ValueError("Invalid PKCE verifier")

        # Return a minimal OpenID Connect token response.
        return {
            "access_token": "fake_access_token_" + secrets.token_hex(8),
            "token_type": "Bearer",
            "expires_in": 3600,
            "refresh_token": "fake_refresh_token_" + secrets.token_hex(8),
            "scope": "openid email",
            "id_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjMwMDA6YWRtaW4iLCJuYW1lIjoiQWRtaW4gVXNlciIsImFzb2MiOiJ2aWV3ZXIiLCJpYXQiOjE2OTk5OTIwMDAsImV4cCI6MTcwMDA1NTYwMH0.fake_signature",
        }

    def create_session_token_from_oidc(
        self, oidc_token: dict[str, Any], user_id: str = "demo-user", role: str = "viewer"
    ) -> str:
        """Wrap OIDC claims into a session token for Lumen Studio."""
        payload = {
            "sub": oidc_token.get("sub", user_id),
            "role": role,
            "preferred_username": oidc_token.get("preferred_username", user_id),
            "email": oidc_token.get("email", ""),
        }
        return create_session_token(payload)


# Singleton instance
oidc = OIDCFlow()
