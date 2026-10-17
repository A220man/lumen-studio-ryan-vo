/**
 * Form for creating a vtable definition.
 *
 * A vtable definition is an ordered list of function-name slots.
 * An empty slot input is stored as ``null`` (unknown/empty), which
 * directly reflects the decompiler scenario in Ghidra issue #516.
 */

import { useState } from "react";
import { api } from "../api/client";
import type { Vtable } from "../api/client";
import "./VtableForm.css";

interface VtableFormProps {
  onCreated: (vtable: Vtable) => void;
}

export default function VtableForm({ onCreated }: VtableFormProps) {
  const [name, setName] = useState("MyClass::vtable");
  const [fieldName, setFieldName] = useState("vtable");
  const [baseAddress, setBaseAddress] = useState("");
  const [slots, setSlots] = useState<string[]>([
    "fn_getType",
    "fn_addRef",
    "",
    "fn_method3",
  ]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function updateSlot(index: number, value: string) {
    setSlots((prev) => {
      const copy = [...prev];
      copy[index] = value;
      return copy;
    });
  }

  function addSlot() {
    setSlots((prev) => [...prev, ""]);
  }

  function removeSlot(index: number) {
    setSlots((prev) => prev.filter((_, i) => i !== index));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const vtable = await api.createVtable({
        name,
        field_name: fieldName,
        base_address: baseAddress || undefined,
        // Empty string → null, preserving the "unknown" slot semantics.
        slots: slots.map((s) => (s.trim() === "" ? null : s.trim())),
      });
      onCreated(vtable);
      // Reset form to empty state after successful save.
      setName("");
      setFieldName("vtable");
      setBaseAddress("");
      setSlots([""]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save vtable");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="vtable-form" onSubmit={handleSubmit} aria-label="Create vtable definition">
      <h2>Define a vtable</h2>

      {error && <div className="form-error">{error}</div>}

      <div className="form-grid">
        <label>
          <span>Name (label)</span>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. MyClass::vtable"
            required
          />
        </label>

        <label>
          <span>Field name (in decompiler)</span>
          <input
            type="text"
            value={fieldName}
            onChange={(e) => setFieldName(e.target.value)}
            placeholder="e.g. vtable"
            required
          />
        </label>

        <label>
          <span>Base address (optional)</span>
          <input
            type="text"
            value={baseAddress}
            onChange={(e) => setBaseAddress(e.target.value)}
            placeholder="e.g. 0x401000"
          />
        </label>
      </div>

      <fieldset className="slot-list">
        <legend>Slots (empty = unknown function)</legend>
        {slots.map((slot, i) => (
          <div key={i} className="slot-row">
            <span className="slot-index">#{i}</span>
            <input
              type="text"
              value={slot}
              onChange={(e) => updateSlot(i, e.target.value)}
              placeholder="function name"
            />
            <button
              type="button"
              className="btn-icon"
              onClick={() => removeSlot(i)}
              aria-label={`Remove slot ${i}`}
            >
              ×
            </button>
          </div>
        ))}
      </fieldset>

      <div className="form-actions">
        <button
          type="button"
          className="btn btn-secondary"
          onClick={addSlot}
          disabled={submitting}
        >
          + Add slot
        </button>
        <button
          type="submit"
          className="btn btn-primary"
          disabled={submitting || !name || !fieldName}
        >
          {submitting ? "Saving…" : "Save vtable"}
        </button>
      </div>
    </form>
  );
}

export type { VtableFormProps };