"""Pydantic request/response schemas for the Lumen Studio API."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

SlotEntry = Optional[str]  # function name or None (unknown slot)


class VtableBase(BaseModel):
    """Shared fields for vtable create/read."""

    name: str = Field(..., description="Human-readable vtable label, e.g. 'MyClass::vtable'")
    field_name: str = Field(
        ...,
        description="Identifier as it appears in the decompiler, e.g. 'vtable'",
    )
    base_address: Optional[str] = Field(
        default=None, description="Optional hex base address string"
    )
    slots: list[SlotEntry] = Field(
        default_factory=list,
        description="Ordered slot list; None = empty/unknown slot",
    )


class VtableCreate(VtableBase):
    pass


class VtableRead(VtableBase):
    """Vtable as stored in the database (adds id + timestamps)."""

    id: int
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class ResolutionMatch(BaseModel):
    """A single matched indirection in the code snippet."""

    line: int
    column: int
    expression: str = Field(..., description="The matched text, e.g. 'vtable[6]'")
    field_name: str = Field(..., description="Field name that was matched")
    slot_index: int
    resolved_function: Optional[str] = Field(
        default=None, description="Function name if resolved, else None"
    )
    note: str = Field(..., description="Human-readable explanation")


class ResolutionResponse(BaseModel):
    """Full resolution result."""

    id: int
    vtable_id: int
    vtable_name: str
    code: str
    matches: list[ResolutionMatch]
    created_at: str


class ResolutionSummary(BaseModel):
    """Lightweight summary for listing past resolutions."""

    id: int
    vtable_id: int
    vtable_name: str
    match_count: int
    created_at: str


class ResolutionRequest(BaseModel):
    """Request body for resolve endpoint."""

    vtable_id: int = Field(..., gt=0)
    code: str = Field(..., min_length=1, max_length=65536)


class VersionInfo(BaseModel):
    """Version endpoint payload."""

    version: str = "unknown"
    env: str = "development"
    demo_mode: bool = False