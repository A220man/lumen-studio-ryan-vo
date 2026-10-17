"""Unit tests for the vtable_resolver domain engine.

These tests exercise the deterministic pattern-matching logic directly,
covering normal cases, boundary indices, empty slots, multiline code,
C++ syntax variants, and the multi-vtable resolver.
"""

from __future__ import annotations

import pytest

from app.services.vtable_resolver import (
    MultiVtableResolver,
    ResolutionMatch,
    VtableDef,
    VtableResolver,
)


# ---------------------------------------------------------------- #
# Basic pattern matching
# ---------------------------------------------------------------- #


class TestSingleFieldResolver:
    """Tests for the single-vtable VtableResolver."""

    def test_resolve_single_call(self, sample_slots):
        resolver = VtableResolver("vtable", sample_slots)
        code = "(*this->vtable[0])(local_20);"
        matches = resolver.resolve(code)
        assert len(matches) == 1
        m = matches[0]
        assert m.field_name == "vtable"
        assert m.slot_index == 0
        assert m.resolved_function == "vtable_getType"
        assert m.line == 1
        assert m.column == 9  # 'v' of vtable[0] at 1-based column 9
        assert m.expression == "vtable[0]"
        assert "resolved to vtable_getType" in m.note

    def test_resolve_multiple_calls(self, sample_slots):
        resolver = VtableResolver("vtable", sample_slots)
        code = """
        (*this->vtable[0])(a);
        (*this->vtable[5])(b);
        (*this->vtable[7])(c);
        """
        matches = resolver.resolve(code)
        assert len(matches) == 3
        assert matches[0].slot_index == 0
        assert matches[0].resolved_function == "vtable_getType"
        assert matches[1].slot_index == 5
        assert matches[1].resolved_function == "vtable_method5"
        assert matches[2].slot_index == 7
        assert matches[2].resolved_function is None
        assert "empty" in matches[2].note

    def test_resolve_bare_field_call(self, sample_slots):
        """Field name without the preceding object/arrow."""
        resolver = VtableResolver("vtable", sample_slots)
        code = "vtable[2]();  // direct call through vtable slot 2"
        matches = resolver.resolve(code)
        assert len(matches) == 1
        assert matches[0].slot_index == 2
        assert matches[0].resolved_function == "vtable_release"

    def test_resolved_column_position(self):
        resolver = VtableResolver("vtable", ["fn_a", "fn_b"])
        code = "  vtable[1]();"
        matches = resolver.resolve(code)
        assert len(matches) == 1
        # 'vtable[1]' starts at column 3 (1-based)
        assert matches[0].column == 3

    def test_multiline_line_numbers(self):
        resolver = VtableResolver("vtable", ["fn_a", "fn_b", "fn_c"])
        code = "line one\nvtable[0]\nline three\nvtable[2]\n"
        matches = resolver.resolve(code)
        assert len(matches) == 2
        assert matches[0].line == 2  # vtable[0] on line 2
        assert matches[1].line == 4  # vtable[2] on line 4


# ---------------------------------------------------------------- #
# Boundary and edge cases
# ---------------------------------------------------------------- #


class TestBoundaryCases:
    def test_index_out_of_range(self, sample_slots):
        resolver = VtableResolver("vtable", sample_slots)
        code = "(*this->vtable[10])(arg);"
        matches = resolver.resolve(code)
        assert len(matches) == 1
        assert matches[0].slot_index == 10
        assert matches[0].resolved_function is None
        assert "out of range" in matches[0].note

    def test_empty_slot_resolves_to_none(self, sample_slots):
        resolver = VtableResolver("vtable", sample_slots)
        code = "vtable[4]();"
        matches = resolver.resolve(code)
        assert len(matches) == 1
        assert matches[0].resolved_function is None
        assert "empty" in matches[0].note

    def test_last_slot_resolves(self):
        resolver = VtableResolver("vtable", ["only_fn"])
        code = "vtable[0]();"
        matches = resolver.resolve(code)
        assert len(matches) == 1
        assert matches[0].resolved_function == "only_fn"

    def test_zero_index(self):
        resolver = VtableResolver("vtable", ["fn_zero", "fn_one"])
        code = "vtable[0]();"
        matches = resolver.resolve(code)
        assert len(matches) == 1
        assert matches[0].resolved_function == "fn_zero"

    def test_empty_code_returns_no_matches(self):
        resolver = VtableResolver("vtable", ["fn_a"])
        assert resolver.resolve("") == []
        assert resolver.resolve("\n\n\n") == []

    def test_no_matching_field_name(self):
        resolver = VtableResolver("vtable", ["fn_a"])
        code = "other_field[0]();"
        assert resolver.resolve(code) == []

    def test_non_integer_index_not_matched(self):
        """Hex or variable indices must not be resolved."""
        resolver = VtableResolver("vtable", ["fn_a", "fn_b"])
        code = "vtable[0x1](); vtable[var]();"
        # Neither hex nor variable indices match the \d+ pattern.
        assert resolver.resolve(code) == []


# ---------------------------------------------------------------- #
# Invalid construction
# ---------------------------------------------------------------- #


class TestConstructionValidation:
    def test_empty_field_name_rejected(self):
        with pytest.raises(ValueError, match="identifier"):
            VtableResolver("", ["fn_a"])

    def test_invalid_identifier_rejected(self):
        with pytest.raises(ValueError, match="identifier"):
            VtableResolver("123bad", ["fn_a"])

    def test_valid_identifier_accepted(self):
        # Underscore is a valid identifier character
        resolver = VtableResolver("_vtable", ["fn_a"])
        code = "_vtable[0]();"
        matches = resolver.resolve(code)
        assert len(matches) == 1
        assert matches[0].resolved_function == "fn_a"


# ---------------------------------------------------------------- #
# Multi-vtable resolver
# ---------------------------------------------------------------- #


class TestMultiVtableResolver:
    def test_resolve_across_multiple_vtables(self):
        mv = MultiVtableResolver()
        mv.add(VtableDef("vt_a", "vtable", None, ["fn_a0", "fn_a1"]))
        mv.add(VtableDef("vt_b", "vftable", None, ["fn_b0", "fn_b1", "fn_b2"]))

        code = (
            "(*this->vtable[1])(x);\n"
            "(*obj->vftable[2])(y);"
        )
        matches = mv.resolve(code)
        assert len(matches) == 2
        a_match = next(m for m in matches if m.field_name == "vtable")
        b_match = next(m for m in matches if m.field_name == "vftable")
        assert a_match.slot_index == 1
        assert a_match.resolved_function == "fn_a1"
        assert b_match.slot_index == 2
        assert b_match.resolved_function == "fn_b2"

    def test_dedup_overlapping_matches(self):
        """Two resolvers with the same field_name should not double-report."""
        mv = MultiVtableResolver()
        mv.add(VtableDef("vt_a", "vtable", None, ["fn_a0"]))
        mv.add(VtableDef("vt_b", "vtable", None, ["fn_b0"]))  # same field name

        code = "vtable[0]();"
        # Same field_name => second add overwrites first in dict
        matches = mv.resolve(code)
        assert len(matches) == 1
        assert matches[0].resolved_function == "fn_b0"

    def test_sorted_output(self):
        mv = MultiVtableResolver()
        mv.add(VtableDef("vt_b", "vtable", None, ["fn_b0", "fn_b1"]))
        code = "vtable[1]();\nvtable[0]();\nvtable[1]();"
        matches = mv.resolve(code)
        assert len(matches) == 3
        # Sorted by line, then column, then slot_index
        assert matches[0].slot_index == 1  # line 1
        assert matches[1].slot_index == 0  # line 2
        assert matches[2].slot_index == 1  # line 3


# ---------------------------------------------------------------- #
# Round-trip: dataclass → dict → Pydantic model
# ---------------------------------------------------------------- #


class TestMatchSerialization:
    def test_to_dict_roundtrip(self):
        resolver = VtableResolver("vtable", ["fn_a"])
        matches = resolver.resolve("vtable[0]();")
        d = matches[0].to_dict()
        assert isinstance(d, dict)
        assert d["slot_index"] == 0
        assert d["resolved_function"] == "fn_a"
        assert d["expression"] == "vtable[0]"