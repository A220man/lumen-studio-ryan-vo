"""OIDC authorization-code callback endpoint for Keycloak PKCE flow."""

from __future__ import annotations

import base64
import json
from typing import Any

from fastapi import APIRouter, Request, Query, HTTPException, status

from ..core.config import settings
from ..core.jwt import create_session_token
from ..core.oidc import oidc
from ..models.schemas import TokenResponse, UserInfo

router = APIRouter(prefix="/api/v1", tags=["oidc"])


def _decode_jwt_payload(token: str) -> dict[str, Any]:
    """Decode the middle section of a JWT without verification (for inspection)."""
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Invalid JWT format")
    payload_b64 = parts[1]
    # Add padding
    payload_b64 += "=" * (-len(payload_b64) % 4)
    return json.loads(base64.urlsafe_b64decode(payload_b64))


@router.get("/oidc/callback", response_model=TokenResponse, summary="Keycloak OIDC authorization-code callback with PKCE")
async def oidc_callback(
    request: Request,
    code: str = Query(..., description="Authorization code from Keycloak"),
    state: str = Query(..., description="State parameter for CSRF protection"),
    session_code_verifier: str = Query(..., description="PKCE code verifier from initial login"),
) -> TokenResponse:
    """Exchange the authorization code for tokens via Keycloak OIDC.

    Validates:
    - State parameter matches stored value (expires after 10 min)
    - PKCE code verifier matches the one generated during login
    - Redirect URI matches
    - Exchanges code for tokens (mocked for demo; real flow posts to Keycloak)
    - Creates a session token from the OIDC claims
    """
    # Validate state - this pops the state from storage (single-use)
    if not oidc.verify_state(state):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired state parameter",
        )

    # Validate PKCE code verifier - do NOT pop it here; let exchange_code_for_tokens handle it
    # Just check it exists and is valid without consuming it
    if session_code_verifier not in oidc._code_verifiers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired PKCE code verifier",
        )

    # In a real implementation, we would POST to Keycloak's token endpoint.
    # For demo mode, exchange the code for a mock token response.
    # This will pop the code_verifier internally.
    token_data = oidc.exchange_code_for_tokens(code, session_code_verifier, str(request.url))

    # Build the id_token payload and create a session token
    # The id_token is a JWT; decode its payload to get claims
    # For the mock token, we construct session token from the claims
    id_token = token_data.get("id_token", "")
    try:
        id_token_payload = _decode_jwt_payload(id_token)
    except Exception:
        id_token_payload = {}

    # Extract claims from the id_token
    sub = id_token_payload.get("sub", "unknown")
    preferred_username = id_token_payload.get("preferred_username", sub)
    email = id_token_payload.get("email", "")

    # Determine role from OIDC claims or default to viewer
    role = id_token_payload.get("role", "viewer")

    # Create session token from OIDC claims
    session_token = create_session_token({
        "sub": sub,
        "role": role,
        "preferred_username": preferred_username,
        "email": email,
        "iss": "lumen-studio",
    })

    # Return token response
    return TokenResponse(
        access_token=token_data.get("access_token", session_token),
        token_type=token_data.get("token_type", "Bearer"),
        expires_in=token_data.get("expires_in", 3600),
        refresh_token=token_data.get("refresh_token", ""),
        scope=token_data.get("scope", "openid email"),
        id_token=id_token,
        session_token=session_token,
        user_info=UserInfo(
            sub=sub,
            email=email,
            preferred_username=preferred_username,
            role=role,
        ),
    )
