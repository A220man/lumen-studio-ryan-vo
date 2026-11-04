/**
 * Unit tests for ResolverPanel keyboard shortcuts and UX improvements.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import ResolverPanel from "../src/components/ResolverPanel";
import type { Vtable } from "../src/api/client";

const mockVtables: Vtable[] = [
  {
    id: 1,
    name: "MyClass::vtable",
    field_name: "vtable",
    base_address: "0x401000",
    slots: ["fn_getType", "fn_addRef", null, "fn_method3"],
    created_at: "2025-01-01T00:00:00Z",
    updated_at: "2025-01-01T00:00:00Z",
  },
];

function makeProps(overrides: Partial<{
  vtables: Vtable[];
  selectedVtableId: number | null;
  onSelectVtable: ReturnType<typeof vi.fn>;
  code: string;
  onCodeChange: ReturnType<typeof vi.fn>;
  onResolve: ReturnType<typeof vi.fn>;
  resolving: boolean;
  error: string | null;
}> = {}) {
  return {
    vtables: mockVtables,
    selectedVtableId: 1,
    onSelectVtable: vi.fn(),
    code: "",
    onCodeChange: vi.fn(),
    onResolve: vi.fn(),
    resolving: false,
    error: null,
    ...overrides,
  };
}

describe("ResolverPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders vtable select with options", () => {
    render(<ResolverPanel {...makeProps()} />);
    expect(screen.getByLabelText("Select vtable for resolution")).toBeInTheDocument();
    expect(screen.getByDisplayValue("MyClass::vtable (#1)")).toBeInTheDocument();
  });

  it("calls onSelectVtable when selection changes", () => {
    const props = makeProps();
    render(<ResolverPanel {...props} />);
    fireEvent.change(screen.getByLabelText("Select vtable for resolution"), {
      target: { value: "1" },
    });
    expect(props.onSelectVtable).toHaveBeenCalledWith(1);
  });

  it("renders code textarea with placeholder hinting Ctrl+Enter", () => {
    render(<ResolverPanel {...makeProps()} />);
    const textarea = screen.getByLabelText("Decompiled code snippet");
    expect(textarea).toHaveAttribute("placeholder", "Paste decompiled C code here… (Ctrl+Enter to resolve)");
  });

  it("calls onCodeChange when code changes", () => {
    const props = makeProps();
    render(<ResolverPanel {...props} />);
    fireEvent.change(screen.getByLabelText("Decompiled code snippet"), {
      target: { value: "(*this->vtable[0])();" },
    });
    expect(props.onCodeChange).toHaveBeenCalledWith("(*this->vtable[0])();");
  });

  it("calls onResolve when Ctrl+Enter is pressed in textarea", () => {
    const props = makeProps({ code: "(*this->vtable[0])();" });
    render(<ResolverPanel {...props} />);
    const textarea = screen.getByLabelText("Decompiled code snippet");
    fireEvent.keyDown(textarea, { key: "Enter", ctrlKey: true });
    expect(props.onResolve).toHaveBeenCalledTimes(1);
  });

  it("calls onResolve when Meta+Enter (macOS) is pressed in textarea", () => {
    const props = makeProps({ code: "(*this->vtable[0])();" });
    render(<ResolverPanel {...props} />);
    const textarea = screen.getByLabelText("Decompiled code snippet");
    fireEvent.keyDown(textarea, { key: "Enter", metaKey: true });
    expect(props.onResolve).toHaveBeenCalledTimes(1);
  });

  it("does not call onResolve when Enter is pressed without modifier", () => {
    const props = makeProps({ code: "(*this->vtable[0])();" });
    render(<ResolverPanel {...props} />);
    const textarea = screen.getByLabelText("Decompiled code snippet");
    fireEvent.keyDown(textarea, { key: "Enter" });
    expect(props.onResolve).not.toHaveBeenCalled();
  });

  it("does not call onResolve when resolving is true", () => {
    const props = makeProps({ code: "(*this->vtable[0])();", resolving: true });
    render(<ResolverPanel {...props} />);
    const textarea = screen.getByLabelText("Decompiled code snippet");
    fireEvent.keyDown(textarea, { key: "Enter", ctrlKey: true });
    expect(props.onResolve).not.toHaveBeenCalled();
  });

  it("does not call onResolve when no vtable selected", () => {
    const props = makeProps({ code: "(*this->vtable[0])();", selectedVtableId: null });
    render(<ResolverPanel {...props} />);
    const textarea = screen.getByLabelText("Decompiled code snippet");
    fireEvent.keyDown(textarea, { key: "Enter", ctrlKey: true });
    expect(props.onResolve).not.toHaveBeenCalled();
  });

  it("does not call onResolve when code is empty", () => {
    const props = makeProps({ code: "" });
    render(<ResolverPanel {...props} />);
    const textarea = screen.getByLabelText("Decompiled code snippet");
    fireEvent.keyDown(textarea, { key: "Enter", ctrlKey: true });
    expect(props.onResolve).not.toHaveBeenCalled();
  });

  it("loads sample code when Use sample button is clicked", () => {
    const props = makeProps();
    render(<ResolverPanel {...props} />);
    fireEvent.click(screen.getByText("Use sample"));
    expect(props.onCodeChange).toHaveBeenCalled();
    const sampleCode = props.onCodeChange.mock.calls[0][0];
    expect(sampleCode).toContain("MyClass::doWork");
    expect(sampleCode).toContain("vtable[0]");
    expect(sampleCode).toContain("vtable[2]");
    expect(sampleCode).toContain("vtable[4]");
  });

  it("disables resolve button when no code", () => {
    render(<ResolverPanel {...makeProps({ code: "" })} />);
    expect(screen.getByText("Resolve calls")).toBeDisabled();
  });

  it("disables resolve button when no vtable selected", () => {
    render(<ResolverPanel {...makeProps({ selectedVtableId: null })} />);
    expect(screen.getByText("Resolve calls")).toBeDisabled();
  });

  it("disables resolve button when resolving", () => {
    render(<ResolverPanel {...makeProps({ resolving: true })} />);
    expect(screen.getByText("Resolving…")).toBeDisabled();
  });

  it("shows error message when error prop is set", () => {
    render(<ResolverPanel {...makeProps({ error: "Vtable not found" })} />);
    expect(screen.getByText("Vtable not found")).toBeInTheDocument();
  });
});

export {};
