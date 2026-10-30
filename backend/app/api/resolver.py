"""Vtable management and indirect-call resolution endpoints.

Routes are protected by ``get_current_user`` in demo mode; in production
OIDC token validation will run through the same dependency (R1: not yet
wired to Keycloak).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query, Response, status

from ..core.database import Database, get_db
from ..models.schemas import (
    ResolutionMatch,
    ResolutionRequest,
    ResolutionResponse,
    ResolutionSummary,
    VtableCreate,
    VtableRead,
)
from ..services.vtable_resolver import VtableResolver
from .dependencies import CurrentUser, get_current_user

router = APIRouter(prefix="/api/v1", tags=["resolver"])


# ------------------------------------------------------------------ #
# Vtable CRUD
# ------------------------------------------------------------------ #


def _row_to_vtable_read(row) -> VtableRead:
    """Convert a sqlite3.Row to a VtableRead schema."""
    return VtableRead(
        id=row["id"],
        name=row["name"],
        field_name=row["field_name"],
        base_address=row["base_address"],
        slots=json.loads(row["slots"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.post("/vtables", response_model=VtableRead, status_code=status.HTTP_201_CREATED)
def create_vtable(
    payload: Annotated[VtableCreate, Body()],
    db: Annotated[Database, Depends(get_db)],
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> VtableRead:
    """Create a vtable definition with an ordered slot list."""
    now = datetime.now(timezone.utc).isoformat()
    cursor = db.execute(
        "INSERT INTO vtables (name, field_name, base_address, slots, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (
            payload.name,
            payload.field_name,
            payload.base_address,
            json.dumps(payload.slots),
            now,
            now,
        ),
    )
    vtable_id = cursor.lastrowid
    if vtable_id is None:
        raise HTTPException(status_code=500, detail="Failed to create vtable")
    return VtableRead(
        id=vtable_id,
        name=payload.name,
        field_name=payload.field_name,
        base_address=payload.base_address,
        slots=payload.slots,
        created_at=now,
        updated_at=now,
    )


@router.get("/vtables", response_model=list[VtableRead])
def list_vtables(
    db: Annotated[Database, Depends(get_db)],
    user: Annotated[CurrentUser, Depends(get_current_user)],
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[VtableRead]:
    """List vtable definitions with pagination."""
    rows = db.query(
        "SELECT * FROM vtables ORDER BY id DESC LIMIT ? OFFSET ?",
        (limit, skip),
    )
    return [_row_to_vtable_read(r) for r in rows]


@router.get("/vtables/{vtable_id}", response_model=VtableRead)
def get_vtable(
    vtable_id: Annotated[int, Path(gt=0)],
    db: Annotated[Database, Depends(get_db)],
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> VtableRead:
    """Retrieve a single vtable definition by id."""
    rows = db.query("SELECT * FROM vtables WHERE id = ?", (vtable_id,))
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vtable {vtable_id} not found",
        )
    return _row_to_vtable_read(rows[0])


@router.delete("/vtables/{vtable_id}")
def delete_vetable(
    vtable_id: Annotated[int, Path(gt=0)],
    db: Annotated[Database, Depends(get_db)],
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> Response:
    """Delete a vtable definition (cascades to its resolutions)."""
    cursor = db.execute("DELETE FROM vtables WHERE id = ?", (vtable_id,))
    if cursor.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vtable {vtable_id} not found",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)

# ------------------------------------------------------------------ #
# Resolution workflow
# ------------------------------------------------------------------ #


def _row_to_summary(row) -> ResolutionSummary:
    return ResolutionSummary(
        id=row["id"],
        vtable_id=row["vtable_id"],
        vtable_name=row["vtable_name"],
        match_count=row["match_count"],
        created_at=row["created_at"],
    )


def _row_to_response(row, db: Database) -> ResolutionResponse:
    """Reconstruct a full ResolutionResponse from a stored row."""
    matches_raw = json.loads(row["matches"])
    matches = [ResolutionMatch(**m) for m in matches_raw]
    # Fetch vtable for base_address
    vtable_rows = db.query("SELECT base_address FROM vtables WHERE id = ?", (row["vtable_id"],))
    base_address = vtable_rows[0]["base_address"] if vtable_rows else None
    return ResolutionResponse(
        id=row["id"],
        vtable_id=row["vtable_id"],
        vtable_name=row["vtable_name"],
        base_address=base_address,
        code=row["code"],
        matches=matches,
        created_at=row["created_at"],
    )


@router.post("/resolutions", response_model=ResolutionResponse, status_code=status.HTTP_201_CREATED)
def create_resolution(
    payload: Annotated[ResolutionRequest, Body()],
    db: Annotated[Database, Depends(get_db)],
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> ResolutionResponse:
    """Resolve indirect calls in *payload.code* using the named vtable.

    The engine scans for ``<field_name>[<integer>]`` patterns and maps
    each index to the function name stored in the vtable's slot list
    (Ghidra issue #516).
    """
    # Look up the vtable
    vtable_rows = db.query("SELECT * FROM vtables WHERE id = ?", (payload.vtable_id,))
    if not vtable_rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vtable {payload.vtable_id} not found",
        )
    vt = vtable_rows[0]
    slots: list[str | None] = json.loads(vt["slots"])

    # Run the deterministic engine
    resolver = VtableResolver(vt["field_name"], slots)
    engine_matches = resolver.resolve(payload.code)

    # Convert engine dataclasses to Pydantic models for storage / response
    match_dicts = [m.to_dict() for m in engine_matches]
    pydantic_matches = [ResolutionMatch(**d) for d in match_dicts]

    now = datetime.now(timezone.utc).isoformat()
    cursor = db.execute(
        "INSERT INTO resolutions (vtable_id, code, matches, created_at) "
        "VALUES (?, ?, ?, ?)",
        (payload.vtable_id, payload.code, json.dumps(match_dicts), now),
    )
    resolution_id = cursor.lastrowid

    return ResolutionResponse(
        id=resolution_id,
        vtable_id=payload.vtable_id,
        vtable_name=vt["name"],
        base_address=vt["base_address"],
        code=payload.code,
        matches=pydantic_matches,
        created_at=now,
    )


@router.get("/resolutions", response_model=list[ResolutionSummary])
def list_resolutions(
    db: Annotated[Database, Depends(get_db)],
    user: Annotated[CurrentUser, Depends(get_current_user)],
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[ResolutionSummary]:
    """List past resolution summaries with pagination."""
    rows = db.query(
        "SELECT r.id, r.vtable_id, v.name as vtable_name, r.created_at, "
        "COUNT(*) as match_count "
        "FROM resolutions r JOIN vtables v ON r.vtable_id = v.id "
        "GROUP BY r.id ORDER BY r.id DESC LIMIT ? OFFSET ?",
        (limit, skip),
    )
    return [_row_to_summary(r) for r in rows]


@router.get("/resolutions/{resolution_id}", response_model=ResolutionResponse)
def get_resolution(
    resolution_id: Annotated[int, Path(gt=0)],
    db: Annotated[Database, Depends(get_db)],
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> ResolutionResponse:
    """Retrieve a past resolution with all matches."""
    rows = db.query(
        "SELECT r.*, v.name as vtable_name "
        "FROM resolutions r JOIN vtables v ON r.vtable_id = v.id "
        "WHERE r.id = ?",
        (resolution_id,),
    )
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resolution {resolution_id} not found",
        )
    return _row_to_response(rows[0], db)