"""Integration tests crossing the HTTP boundary for the core workflow.

Tests cover the full create-vtable → resolve → retrieve → delete cycle
using an isolated in-memory SQLite database (see conftest.py).
"""

from __future__ import annotations

import json

from fastapi import status


# ---------------------------------------------------------------- #
# Helpers
# ---------------------------------------------------------------- #


def _create_vtable(
    client,
    name: str = "MyClass::vtable",
    field_name: str = "vtable",
    slots: list = None,
    base_address: str | None = "0x401000",
) -> int:
    """Create a vtable via the API and return its id."""
    if slots is None:
        slots = ["fn_getType", "fn_addRef", None, "fn_method3"]
    resp = client.post(
        "/api/v1/vtables",
        json={
            "name": name,
            "field_name": field_name,
            "base_address": base_address,
            "slots": slots,
        },
    )
    assert resp.status_code == status.HTTP_201_CREATED
    return resp.json()["id"]


# ---------------------------------------------------------------- #
# Vtable CRUD
# ---------------------------------------------------------------- #


class TestVtableCRUD:
    def test_create_vtable(self, client):
        slots = ["fn_a", "fn_b", None]
        resp = client.post(
            "/api/v1/vtables",
            json={
                "name": "TestClass::vtable",
                "field_name": "vtable",
                "base_address": "0x1000",
                "slots": slots,
            },
        )
        assert resp.status_code == status.HTTP_201_CREATED
        body = resp.json()
        assert body["name"] == "TestClass::vtable"
        assert body["field_name"] == "vtable"
        assert body["base_address"] == "0x1000"
        assert body["slots"] == slots
        assert body["id"] is not None
        assert body["created_at"] is not None
        assert body["updated_at"] == body["created_at"]

    def test_create_vtable_validation_error(self, client):
        """Empty slots list is allowed; missing field_name is rejected."""
        resp = client.post(
            "/api/v1/vtables",
            json={
                "name": "Bad",
                "base_address": "0x1000",
                "slots": [],
            },
        )
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_get_vtable_by_id(self, client):
        vt_id = _create_vtable(client)
        resp = client.get(f"/api/v1/vtables/{vt_id}")
        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert body["id"] == vt_id
        assert body["name"] == "MyClass::vtable"
        assert body["field_name"] == "vtable"
        assert body["slots"] == ["fn_getType", "fn_addRef", None, "fn_method3"]

    def test_get_vtable_not_found(self, client):
        resp = client.get("/api/v1/vtables/99999")
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_list_vtables(self, client):
        _create_vtable(client, name="vtable_a", field_name="vtable")
        _create_vtable(client, name="vtable_b", field_name="vtable")
        resp = client.get("/api/v1/vtables")
        assert resp.status_code == status.HTTP_200_OK
        vtables = resp.json()
        assert len(vtables) == 2
        # Newest first
        assert vtables[0]["name"] == "vtable_b"
        assert vtables[1]["name"] == "vtable_a"

    def test_list_vtables_pagination(self, client):
        for i in range(5):
            _create_vtable(client, name=f"vt_{i}", field_name="vtable")
        resp = client.get("/api/v1/vtables?skip=2&limit=2")
        assert resp.status_code == status.HTTP_200_OK
        vtables = resp.json()
        assert len(vtables) == 2

    def test_delete_vtable(self, client):
        vt_id = _create_vtable(client)
        resp = client.delete(f"/api/v1/vtables/{vt_id}")
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        # Verify deletion
        resp = client.get(f"/api/v1/vtables/{vt_id}")
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_vtable_not_found(self, client):
        resp = client.delete("/api/v1/vtables/99999")
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_vtable_cascades_resolutions(self, client):
        """Deleting a vtable should cascade-delete its resolutions."""
        vt_id = _create_vtable(client)
        # Create a resolution
        resp = client.post(
            "/api/v1/resolutions",
            json={"vtable_id": vt_id, "code": "vtable[0]();"},
        )
        assert resp.status_code == status.HTTP_201_CREATED
        res_id = resp.json()["id"]
        # Delete vtable
        client.delete(f"/api/v1/vtables/{vt_id}")
        # Resolution should be gone (cascade)
        resp = client.get(f"/api/v1/resolutions/{res_id}")
        assert resp.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------- #
# Resolution workflow (end-to-end)
# ---------------------------------------------------------------- #


class TestResolutionWorkflow:
    def test_resolve_returns_expected_matches(self, client):
        """The core end-to-end workflow: create vtable → resolve → verify."""
        vt_id = _create_vtable(client)
        code = """
        void MyClass::doWork() {
            (*this->vtable[0])(arg1);    // should resolve to fn_getType
            (*this->vtable[2])(arg2);    // slot 2 is empty → None
            (*this->vtable[10])(arg3);   // out of range → None
        }
        """
        resp = client.post(
            "/api/v1/resolutions",
            json={"vtable_id": vt_id, "code": code},
        )
        assert resp.status_code == status.HTTP_201_CREATED
        body = resp.json()
        assert body["vtable_id"] == vt_id
        assert body["vtable_name"] == "MyClass::vtable"
        assert body["base_address"] == "0x401000"  # default vtable has base_address
        assert body["code"] == code
        assert len(body["matches"]) == 3

        # Slot 0 → resolved
        m0 = body["matches"][0]
        assert m0["slot_index"] == 0
        assert m0["resolved_function"] == "fn_getType"
        assert m0["line"] == 3
        assert "vtable[0]" in m0["expression"]

        # Slot 2 → empty
        m2 = body["matches"][1]
        assert m2["slot_index"] == 2
        assert m2["resolved_function"] is None
        assert "empty" in m2["note"]

        # Slot 10 → out of range
        m10 = body["matches"][2]
        assert m10["slot_index"] == 10
        assert m10["resolved_function"] is None
        assert "out of range" in m10["note"]

    def test_resolve_vtable_not_found(self, client):
        resp = client.post(
            "/api/v1/resolutions",
            json={"vtable_id": 99999, "code": "vtable[0]();"},
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_resolve_empty_code(self, client):
        vt_id = _create_vtable(client)
        resp = client.post(
            "/api/v1/resolutions",
            json={"vtable_id": vt_id, "code": ""},
        )
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_resolve_code_too_long(self, client):
        vt_id = _create_vtable(client)
        resp = client.post(
            "/api/v1/resolutions",
            json={"vtable_id": vt_id, "code": "x" * 100_000},
        )
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_get_resolution_after_create(self, client):
        """Persisted resolution must be retrievable."""
        vt_id = _create_vtable(client, base_address="0x1000")
        resp = client.post(
            "/api/v1/resolutions",
            json={"vtable_id": vt_id, "code": "vtable[1]();"},
        )
        res_id = resp.json()["id"]

        resp = client.get(f"/api/v1/resolutions/{res_id}")
        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert body["id"] == res_id
        assert body["base_address"] == "0x1000"
        assert len(body["matches"]) == 1
        assert body["matches"][0]["resolved_function"] == "fn_addRef"

    def test_get_resolution_not_found(self, client):
        resp = client.get("/api/v1/resolutions/99999")
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_list_resolutions(self, client):
        vt_id = _create_vtable(client)
        # Create two resolutions
        for code in ["vtable[0]();", "vtable[3]();"]:
            client.post(
                "/api/v1/resolutions",
                json={"vtable_id": vt_id, "code": code},
            )
        resp = client.get("/api/v1/resolutions")
        assert resp.status_code == status.HTTP_200_OK
        summaries = resp.json()
        assert len(summaries) == 2
        assert all(s["vtable_name"] == "MyClass::vtable" for s in summaries)

    def test_resolve_no_matches(self, client):
        """Code with no indirection patterns returns empty matches list."""
        vt_id = _create_vtable(client)
        resp = client.post(
            "/api/v1/resolutions",
            json={"vtable_id": vt_id, "code": "int main() { return 0; }"},
        )
        assert resp.status_code == status.HTTP_201_CREATED
        body = resp.json()
        assert body["matches"] == []

    def test_resolve_uses_correct_vtable(self, client):
        """Different vtables with different field names resolve independently."""
        # Vtable A uses field name "vtable"
        vt_a_id = _create_vtable(
            client, name="VTA", field_name="vtable",
            slots=["fn_a0", "fn_a1"], base_address="0x1000",
        )
        # Vtable B uses field name "vftable"
        vt_b_id = _create_vtable(
            client, name="VTB", field_name="vftable",
            slots=["fn_b0", "fn_b1", "fn_b2"], base_address="0x2000",
        )
        code = (
            "(*this->vtable[1])(x);\n"      # vt_a slot 1
            "(*obj->vftable[2])(y);"        # vt_b slot 2
        )
        # Resolve with vt_a
        resp_a = client.post(
            "/api/v1/resolutions",
            json={"vtable_id": vt_a_id, "code": code},
        )
        body_a = resp_a.json()
        assert len(body_a["matches"]) == 1  # only vtable[1] matches
        assert body_a["matches"][0]["resolved_function"] == "fn_a1"

        # Resolve with vt_b
        resp_b = client.post(
            "/api/v1/resolutions",
            json={"vtable_id": vt_b_id, "code": code},
        )
        body_b = resp_b.json()
        assert len(body_b["matches"]) == 1  # only vftable[2] matches
        assert body_b["matches"][0]["resolved_function"] == "fn_b2"