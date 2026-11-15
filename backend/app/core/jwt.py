"""Simple JWT-like token for session management."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any

from .config import settings


def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _base64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def create_session_token(payload: dict[str, Any], expires_in: int = 3600) -> str:
    """Create a signed session token using HMAC-SHA256."""
    header = {"alg": "HS256", "typ": "JWT"}
    now = int(time.time())
    token_payload = {**payload, "iat": now, "exp": now + expires_in, "iss": "lumen-studio"}

    header_b64 = _base64url_encode(json.dumps(header, separators=(",", ":")).encode())
    payload_b64 = _base64url_encode(json.dumps(token_payload, separators=(",", ":")).encode())
    message = f"{header_b64}.{payload_b64}"
    # HMAC-SHA256 signature
    key = settings.session_secret.encode()
    signature = hmac.new(key, message.encode(), hashlib.sha256).digest()
    signature_b64 = _base64url_encode(signature)
    return f"{message}.{signature_b64}"


def verify_session_token(token: str) -> dict[str, Any] | None:
    """Verify token signature and return payload."""
    try:
        header_b64, payload_b64, signature_b64 = token.split(".")
        # Verify signature
        key = settings.session_secret.encode()
        message = f"{header_b64}.{payload_b64}"
        expected = hmac.new(key, message.encode(), hashlib.sha256).digest()
        expected_b64 = _base64url_encode(expected)
        if not hmac.compare_digest(expected_b64, signature_b64):
            return None

        payload = json.loads(_base64url_decode(payload_b64).decode())
        now = int(time.time())
        if payload.get("exp", 0) < now:
            return None
        return payload
    except Exception:
        return None
