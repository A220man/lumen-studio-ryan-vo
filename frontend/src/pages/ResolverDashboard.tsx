/**
 * ResolverDashboard — the main page.
 *
 * Coordinates the full workflow:
 * 1. List existing vtables and create new ones (VtableForm).
 * 2. Select a vtable, paste decompiled code, and resolve indirect calls
 *    (ResolverPanel).
 * 3. Inspect resolved function calls, their positions, and export as JSON
 *    (ResultsList).
 */

import { useEffect, useState } from "react";
import VtableForm from "../components/VtableForm";
import ResolverPanel from "../components/ResolverPanel";
import ResultsList from "../components/ResultsList";
import { api } from "../api/client";
import type { Resolution, Vtable } from "../api/client";
import "./ResolverDashboard.css";

const EMPTY_CODE = "";

export default function ResolverDashboard() {
  const [vtables, setVtables] = useState<Vtable[]>([]);
  const [selectedVtableId, setSelectedVtableId] = useState<number | null>(null);
  const [code, setCode] = useState(EMPTY_CODE);
  const [resolution, setResolution] = useState<Resolution | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // ---------------------------------------------------------------- #
  // Data fetching / mutation
  // ---------------------------------------------------------------- #

  const loadVtables = () => {
    setLoading(true);
    api
      .listVtables()
      .then(setVtables)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load vtables"))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadVtables();
  }, []);

  function handleVtableCreated(vt: Vtable) {
    setVtables((prev) => [vt, ...prev]);
    setSelectedVtableId(vt.id);
    setResolution(null);
  }

  function handleDeleteVtable(id: number) {
    api
      .deleteVtable(id)
      .then(() => {
        setVtables((prev) => prev.filter((v) => v.id !== id));
        if (selectedVtableId === id) {
          setSelectedVtableId(null);
          setResolution(null);
        }
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to delete"));
  }

  // ---------------------------------------------------------------- #
  // Resolution
  // ---------------------------------------------------------------- #

  async function handleResolve() {
    if (!selectedVtableId || !code.trim()) return;

    setLoading(true);
    setError(null);
    setResolution(null);
    try {
      const result = await api.createResolution({
        vtable_id: selectedVtableId,
        code,
      });
      setResolution(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Resolution failed");
    } finally {
      setLoading(false);
    }
  }

  function handleExport(res: Resolution) {
    const blob = new Blob([JSON.stringify(res, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `resolution-${res.id}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  // ---------------------------------------------------------------- #

  return (
    <div className="dashboard">
      <section className="section">
        <h2>Vtable definitions</h2>

        <VtableForm onCreated={handleVtableCreated} />

        {error && <div className="error-banner" style={{ padding: "0.4rem 0.75rem", borderRadius: "0.3rem", background: "#fee2e2", color: "#991b2b" }}>{error}</div>}

        {vtables.length > 0 ? (
          <div className="vtable-list">
            {vtables.map((vt) => (
              <div
                key={vt.id}
                className={`vtable-item ${selectedVtableId === vt.id ? "selected" : ""}`}
                onClick={() => setSelectedVtableId(vt.id)}
              >
                <div className="vtable-info">
                  <span className="vtable-name">{vt.name}</span>
                  <span className="vtable-slots">
                    {vt.slots.filter((s) => s != null).length} of {vt.slots.length}{" "}
                    slots mapped · field: <code>{vt.field_name}</code>
                  </span>
                </div>
                <div className="vtable-actions">
                  <button
                    type="button"
                    className="btn btn-danger btn-icon"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeleteVtable(vt.id);
                    }}
                    aria-label={`Delete ${vt.name}`}
                  >
                    ×
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="no-vtables">No vtables yet. Define one above.</p>
        )}
      </section>

      <div className="dashboard-grid">
        <section className="section">
          <ResolverPanel
            vtables={vtables}
            selectedVtableId={selectedVtableId}
            onSelectVtable={setSelectedVtableId}
            code={code}
            onCodeChange={setCode}
            onResolve={handleResolve}
            resolving={loading}
            error={error}
          />
        </section>

        <section className="section">
          <ResultsList resolution={resolution} onExport={handleExport} />
        </section>
      </div>
    </div>
  );
}