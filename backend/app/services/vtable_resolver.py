"""Domain engine: resolve indirect vtable calls in decompiled C code.

Given a *vtable definition* (an ordered list of function-name slots,
where ``None`` marks an empty/unknown slot) and a decompiled code
snippet, the resolver:

1. Scans the snippet for ``FIELD[INTEGER]`` indirection patterns using
   the configured field name (e.g. ``vtable``).
2. Looks up the integer index in the slot list.
3. Emits a resolution record with line/column context and either the
   resolved function name or an advisory note.

This directly addresses Ghidra issue #516: instead of seeing
``(*this->vtable[6])(local_20)`` and manually checking the listing to
discover *which* function slot 6 maps to, the analyst gets the answer
immediately.

The engine is fully deterministic and offline — no LLM key is required.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Optional


@dataclass(frozen=True)
class ResolutionMatch:
    """A single matched indirection with resolution context."""

    line: int          # 1-based line number
    column: int        # 1-based column number
    expression: str    # the matched text, e.g. 'vtable[6]'
    field_name: str    # field name that was matched, e.g. 'vtable'
    slot_index: int    # the integer index parsed from the bracket
    resolved_function: Optional[str]  # function name if resolved, else None
    note: str          # human-readable explanation

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class VtableDef:
    """A vtable definition with ordered slots."""

    name: str
    field_name: str
    base_address: Optional[str]
    slots: list[Optional[str]]

    @classmethod
    def from_row(cls, row: dict) -> "VtableDef":
        return cls(
            name=row["name"],
            field_name=row["field_name"],
            base_address=row.get("base_address"),
            slots=row["slots"],
        )


class VtableResolver:
    """Resolves ``field_name[INDEX]`` patterns to function names.

    Parameters
    ----------
    field_name:
        The identifier as it appears in the decompiler output, e.g.
        ``"vtable"``.  The resolver only matches this exact name so that
        a snippet referencing multiple vtables can be resolved by
        creating a separate resolver per vtable.
    slots:
        Ordered list of function names.  ``None`` marks an empty or
        unknown slot.  Index 0 is the first slot (matching C array
        semantics).
    """

    def __init__(self, field_name: str, slots: list[Optional[str]]) -> None:
        if not field_name or not field_name.isidentifier():
            raise ValueError(f"field_name must be a valid identifier, got {field_name!r}")
        self.field_name = field_name
        self.slots = list(slots)
        # Pattern: word boundary + field name + [ + integer + ]
        # Captures the index group for easy extraction.
        self._pattern = re.compile(
            rf"\b{re.escape(field_name)}\s*\[\s*(\d+)\s*\]"
        )

    def resolve(self, code: str) -> list[ResolutionMatch]:
        """Resolve all indirection patterns in *code*.

        Returns matches sorted by line/column position.
        """
        if not code:
            return []

        matches: list[ResolutionMatch] = []

        for m in self._pattern.finditer(code):
            full_expr = m.group(0)
            index = int(m.group(1))

            line, col = self._position(code, m.start())

            resolved, note = self._lookup(index)

            matches.append(
                ResolutionMatch(
                    line=line,
                    column=col,
                    expression=full_expr,
                    field_name=self.field_name,
                    slot_index=index,
                    resolved_function=resolved,
                    note=note,
                )
            )

        return matches

    # -- internal helpers ------------------------------------------------

    def _lookup(self, index: int) -> tuple[Optional[str], str]:
        """Return (function_name_or_None, note) for a slot index."""
        if index < 0:
            return None, f"slot {index} is negative (invalid)"
        if index >= len(self.slots):
            return (
                None,
                f"slot {index} is out of range; vtable has "
                f"{len(self.slots)} slots (indices 0–{max(0, len(self.slots) - 1)})",
            )
        fn = self.slots[index]
        if fn is None:
            return None, f"slot {index} is empty (no function assigned)"
        return fn, f"resolved to {fn}"

    @staticmethod
    def _position(code: str, offset: int) -> tuple[int, int]:
        """Convert a byte offset into (1-based line, 1-based column)."""
        # Count newlines before offset for line number.
        line = code.count("\n", 0, offset) + 1
        # Find start of current line.
        line_start = code.rfind("\n", 0, offset) + 1
        col = offset - line_start + 1
        return line, col


# -- Multi-vtable support --------------------------------------------------


class MultiVtableResolver:
    """Resolve code that may reference several different vtables.

    Each sub-resolver matches a specific field name.  This class
    iterates all registered resolvers and collects their matches,
    de-duplicating by exact (line, column, expression) tuples.
    """

    def __init__(self) -> None:
        self._resolvers: dict[str, VtableResolver] = {}

    def add(self, vtable_def: VtableDef) -> None:
        """Register a vtable definition by its field_name."""
        self._resolvers[vtable_def.field_name] = VtableResolver(
            vtable_def.field_name, vtable_def.slots
        )

    def resolve(self, code: str) -> list[ResolutionMatch]:
        all_matches: list[ResolutionMatch] = []
        seen: set[tuple[int, int, str]] = set()

        for resolver in self._resolvers.values():
            for match in resolver.resolve(code):
                key = (match.line, match.column, match.expression)
                if key not in seen:
                    seen.add(key)
                    all_matches.append(match)

        # Sort by position for deterministic output.
        all_matches.sort(key=lambda m: (m.line, m.column, m.slot_index))
        return all_matches