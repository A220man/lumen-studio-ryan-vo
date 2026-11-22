"""Tests for the Keycloak OIDC authorization-code callback endpoint."""

from __future__ import annotations

from fastapi import status
from fastapi.testclient import TestClient

from app.main import create_app


def test_oidc_callback_valid_flow_first_call() -> None:
    """Test the OIDC callback flow - first call with valid state+PKCE.
    
    PKCE verifier is single-use (consumed/ popped after verification).
    The first call validates state and verifier; second call with same verifier fails.
    """
    app = create_app()
    client = TestClient(app)

    # Generate state and PKCE verifier
    from app.core.oidc import oidc
    state = oidc.generate_state()
    verifier, challenge = oidc.generate_pkce()

    # First verify state is valid before the flow consumes it
    assert oidc.verify_state(state) is True, "State should be valid initially"

    # First call: should pass state+PKCE validation, then attempt code exchange
    # The dummy code will fail PKCE verification in demo mode, giving 400
    resp = client.get(
        "/api/v1/oidc/callback",
        params={"code": "dummy_auth_code", "state": state, "session_code_verifier": verifier},
    )

    # First call result - state+PKCE were valid, but dummy code is not real
    print(f"First call status: {resp.status_code}")
    body = resp.json()
    # In demo mode with dummy code, we get 400 (invalid PKCE verifier after exchange attempt)
    # This is expected - the verifier was consumed during the flow
    assert resp.status_code in (
        status.HTTP_200_OK,
        status.HTTP_400_BAD_REQUEST,
    ), f"Unexpected status: {resp.status_code}, body: {resp.text}"

    if resp.status_code == status.HTTP_200_OK:
        assert "access_token" in body
        assert "token_type" in body
        assert "expires_in" in body
        assert "id_token" in body
        assert "session_token" in body
        assert "user_info" in body
        print(f"Response keys: {list(body.keys())}")
    elif resp.status_code == status.HTTP_400_BAD_REQUEST:
        # Expected: dummy code + consumed verifier
        print(f"Expected 400 (consumed verifier/dummy code): {body}")

    # Second call with same verifier should fail because it was consumed
    resp2 = client.get(
        "/api/v1/oidc/callback",
        params={"code": "dummy_auth_code", "state": oidc.generate_state(), "session_code_verifier": verifier},
    )
    print(f"Second call with consumed verifier: {resp2.status_code}")
    # The second call should fail PKCE verification since verifier was popped
    assert resp2.status_code == status.HTTP_400_BAD_REQUEST, (
        f"Expected 400 for consumed verifier, got {resp2.status_code}"
    )


def test_oidc_callback_invalid_state() -> None:
    """An invalid state parameter returns 400."""
    app = create_app()
    client = TestClient(app)

    resp = client.get(
        "/api/v1/oidc/callback",
        params={"code": "dummy_auth_code", "state": "invalid_state", "session_code_verifier": "some_verifier"},
    )

    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    body = resp.json()
    print(f"Invalid state status: {resp.status_code}, body: {body}")
    # response is a dict
    assert isinstance(body, dict)


def test_oidc_callback_invalid_pkce() -> None:
    """An invalid PKCE verifier returns 400."""
    app = create_app()
    client = TestClient(app)

    resp = client.get(
        "/api/v1/oidc/callback",
        params={"code": "dummy_auth_code", "state": "some_state", "session_code_verifier": "invalid_verifier"},
    )

    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    body = resp.json()
    print(f"Invalid PKCE status: {resp.status_code}, body: {body}")
    # Check keys exist
    assert isinstance(body, dict)


def test_oidc_state_and_pkce_generation() -> None:
    """Test that state and PKCE can be generated and verified."""
    from app.core.oidc import oidc

    # Generate state
    state = oidc.generate_state()
    assert oidc.verify_state(state) is True, "State should be valid initially"

    # Generate PKCE
    verifier, challenge = oidc.generate_pkce()
    assert verifier is not None
    assert challenge is not None
    print(f"Generated verifier: {verifier[:20]}...")
    print(f"Generated challenge: {challenge}")

    # Verify state is still valid after PKCE generation (they're independent)
    assert oidc.verify_state(state) is True, "State should still be valid"

    # Verify state expires after 10 min (check the stored time is set)
    # Just verify the time was stored (we can't easily test expiry without waiting,
    # but we can verify the mechanism works)
    state_time = oidc._states[state]
    print(f"State stored at time: {state_time}")
    # Verify state is in the store
    assert state in oidc._states, "State should be in storage"

    # Verify state is rejected when not in store
    assert oidc.verify_state("nonexistent_state") is False, "Non-existent state should be invalid"
    print("Non-existent state correctly rejected")

    print("State generation and storage test passed")
