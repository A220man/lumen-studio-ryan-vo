/**
 * Frontend tests for the resolver dashboard workflow.
 *
 * The API client is mocked so we can verify user-visible behaviour
 * (form submission, resolution display, error handling) without a
 * running backend.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import ResolverDashboard from "../src/pages/ResolverDashboard";
import type { Resolution as ResolutionType, Vtable as VtableType } from "../src/api/client";

// ── Hoisted mocks so they exist before vi.mock is evaluated ─────────

const mocks = vi.hoisted(() => ({
  listVtables: vi.fn(),
  createVtable: vi.fn(),
  deleteVtable: vi.fn(),
  createResolution: vi.fn(),
  getResolution: vi.fn(),
  listResolutions: vi.fn(),
  health: vi.fn(),
  version: vi.fn(),
}));

// ── Module mock ─────────────────────────────────────────────────────

vi.mock("../src/api/client", () => ({
  api: mocks,
}));

// ── Helpers ──────────────────────────────────────────────────────────

const makeVtable = (overrides = {}): VtableType => ({
  id: 1,
  name: "MyClass::vtable",
  field_name: "vtable",
  base_address: "0x401000",
  slots: ["fn_getType", "fn_addRef", null, "fn_method3"],
  created_at: "2025-01-01T00:00:00Z",
  updated_at: "2025-01-01T00:00:00Z",
  ...overrides,
});

const makeResolution = (overrides = {}): ResolutionType => ({
  id: 1,
  vtable_id: 1,
  vtable_name: "MyClass::vtable",
  code: "vtable[0]();",
  matches: [
    {
      line: 1,
      column: 1,
      expression: "vtable[0]",
      field_name: "vtable",
      slot_index: 0,
      resolved_function: "fn_getType",
      note: "resolved to fn_getType",
    },
  ],
  created_at: "2025-01-01T00:00:00Z",
  ...overrides,
});

describe("ResolverDashboard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.listVtables.mockResolvedValue([]);
    mocks.health.mockResolvedValue({ status: "ok", service: "lumen-studio" });
    mocks.version.mockResolvedValue({
      version: "1.0.0",
      env: "development",
      demo_mode: true,
    });
  });

  it("renders empty state when no vtables exist", async () => {
    render(<ResolverDashboard />);

    await waitFor(() => {
      expect(screen.getByText(/No vtables yet/)).toBeInTheDocument();
    });
  });

  it("loads and displays existing vtables", async () => {
    mocks.listVtables.mockResolvedValue([
      makeVtable({ id: 1, name: "First" }),
      makeVtable({ id: 2, name: "Second" }),
    ]);

    render(<ResolverDashboard />);

    await waitFor(() => {
      expect(screen.getByText("First")).toBeInTheDocument();
      expect(screen.getByText("Second")).toBeInTheDocument();
    });
  });

  it("creates a vtable and shows it in the list", async () => {
    mocks.listVtables.mockResolvedValue([]);
    const newVtable = makeVtable({ id: 5, name: "NewVtable" });
    mocks.createVtable.mockResolvedValue(newVtable);

    render(<ResolverDashboard />);

    await waitFor(() => {
      expect(screen.getByText("Define a vtable")).toBeInTheDocument();
    });

    const nameInput = screen.getByPlaceholderText("e.g. MyClass::vtable");
    fireEvent.change(nameInput, { target: { value: "NewVtable" } });

    const saveButton = screen.getByText("Save vtable");
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(mocks.createVtable).toHaveBeenCalledWith(
        expect.objectContaining({
          name: "NewVtable",
          field_name: "vtable",
          slots: [expect.any(String), expect.any(String), null, expect.any(String)],
        }),
      );
      expect(screen.getByText("NewVtable")).toBeInTheDocument();
    });
  });

  it("resolves indirect calls and displays results", async () => {
    mocks.listVtables.mockResolvedValue([makeVtable({ id: 1 })]);
    mocks.createResolution.mockResolvedValue(
      makeResolution({
        vtable_id: 1,
        code: "vtable[0]();",
        matches: [
          {
            line: 1,
            column: 1,
            expression: "vtable[0]",
            field_name: "vtable",
            slot_index: 0,
            resolved_function: "fn_getType",
            note: "resolved to fn_getType",
          },
        ],
      }),
    );

    render(<ResolverDashboard />);

    await waitFor(() => {
      expect(screen.getByText("MyClass::vtable")).toBeInTheDocument();
    });

    // Select the vtable.
    fireEvent.click(screen.getByText("MyClass::vtable"));

    // Enter code into the now-enabled textarea.
    fireEvent.change(screen.getByLabelText("Decompiled code snippet"), {
      target: { value: "vtable[0]();" },
    });

    // Click resolve.
    fireEvent.click(screen.getByText("Resolve calls"));

    await waitFor(() => {
      expect(mocks.createResolution).toHaveBeenCalledWith({
        vtable_id: 1,
        code: "vtable[0]();",
      });
      expect(screen.getByText("fn_getType")).toBeInTheDocument();
    });
  });

  it("shows error when resolution fails", async () => {
    mocks.listVtables.mockResolvedValue([makeVtable({ id: 1 })]);
    mocks.createResolution.mockRejectedValue(
      new Error("Vtable 99999 not found"),
    );

    render(<ResolverDashboard />);

    await waitFor(() => {
      expect(screen.getByText("MyClass::vtable")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("MyClass::vtable"));

    fireEvent.change(screen.getByLabelText("Decompiled code snippet"), {
      target: { value: "vtable[0]();" },
    });

    fireEvent.click(screen.getByText("Resolve calls"));

    await waitFor(() => {
      expect(screen.getAllByText(/Vtable 99999 not found/).length).toBeGreaterThan(0);
    });
  });
});