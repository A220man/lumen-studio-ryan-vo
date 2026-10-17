"""Tests for the health-check and version endpoints."""

from __future__ import annotations

from fastapi import status


def test_health_returns_ok(client):
    resp = client.get("/api/v1/health")
    assert resp.status_code == status.HTTP_200_OK
    body = resp.json()
    assert body["status"] == "ok"
    assert body["service"] == "lumen-studio"


def test_version_returns_metadata(client):
    resp = client.get("/api/v1/version")
    assert resp.status_code == status.HTTP_200_OK
    body = resp.json()
    assert "version" in body
    assert "env" in body
    assert "demo_mode" in body
    assert body["demo_mode"] is True  # demo mode is on in tests
    assert body["version"] != ""