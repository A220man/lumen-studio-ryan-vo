/**
 * Panel for selecting a vtable, pasting decompiled code, and
 * triggering the resolution engine.
 */

import { useEffect, useRef } from "react";
import type { Vtable } from "../api/client";
import "./ResolverPanel.css";

interface ResolverPanelProps {
  vtables: Vtable[];
  selectedVtableId: number | null;
  onSelectVtable: (id: number) => void;
  code: string;
  onCodeChange: (code: string) => void;
  onResolve: () => void;
  resolving: boolean;
  error: string | null;
}

const SAMPLE_CODE = `void MyClass::doWork(int arg1, int arg2) {
    (*this->vtable[0])(arg1);    // expect fn_getType
    (*this->vtable[2])(arg1, arg2); // slot 2 is empty
    (*this->vtable[4])(arg1);    // out of range
    int x = arg1 + arg2;
}`;

export default function ResolverPanel({
  vtables,
  selectedVtableId,
  onSelectVtable,
  code,
  onCodeChange,
  onResolve,
  resolving,
  error,
}: ResolverPanelProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Ctrl+Enter to resolve
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
        e.preventDefault();
        if (!resolving && selectedVtableId && code.trim()) {
          onResolve();
        }
      }
    }

    const textarea = textareaRef.current;
    if (textarea) {
      textarea.addEventListener("keydown", handleKeyDown);
    }
    return () => {
      if (textarea) {
        textarea.removeEventListener("keydown", handleKeyDown);
      }
    };
  }, [resolving, selectedVtableId, code, onResolve]);

  return (
    <div className="resolver-panel">
      <h2>Resolve indirect calls</h2>

      <label className="field-select-label">
        <span>Vtable</span>
        <select
          value={selectedVtableId ?? ""}
          onChange={(e) => onSelectVtable(Number(e.target.value))}
          disabled={resolving || vtables.length === 0}
          aria-label="Select vtable for resolution"
        >
          <option value="" disabled>
            {vtables.length === 0 ? "No vtables defined" : "Choose a vtable"}
          </option>
          {vtables.map((vt) => (
            <option key={vt.id} value={vt.id}>
              {vt.name} (#{vt.id})
            </option>
          ))}
        </select>
      </label>

      <label className="code-input-label">
        <span>Decompiled code</span>
        <textarea
          ref={textareaRef}
          value={code}
          onChange={(e) => onCodeChange(e.target.value)}
          placeholder="Paste decompiled C code here… (Ctrl+Enter to resolve)"
          rows={10}
          disabled={resolving || !selectedVtableId}
          aria-label="Decompiled code snippet"
        />
      </label>

      {error && <div className="resolve-error">{error}</div>}

      <div className="panel-actions">
        <button
          type="button"
          className="btn btn-primary"
          onClick={onResolve}
          disabled={resolving || !selectedVtableId || !code.trim()}
        >
          {resolving ? "Resolving…" : "Resolve calls"}
        </button>

        <button
          type="button"
          className="btn btn-secondary"
          onClick={() => {
            onCodeChange(SAMPLE_CODE);
          }}
          disabled={resolving || !selectedVtableId}
        >
          Use sample
        </button>
      </div>
    </div>
  );
}

export type { ResolverPanelProps };
