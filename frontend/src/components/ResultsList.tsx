/**
 * Display resolved indirect calls in a table with JSON export.
 *
 * Each row shows the line/column location, the matched expression,
 * the slot index, the resolved function name (or advisory note),
 * and a color-coded status.
 */

import type { Resolution, ResolutionMatch } from "../api/client";
import "./ResultsList.css";

interface ResultsListProps {
  resolution: Resolution | null;
  onExport: (resolution: Resolution) => void;
}

function statusForMatch(m: ResolutionMatch): "resolved" | "empty" | "out-of-range" {
  if (m.resolved_function) return "resolved";
  if (m.note.includes("empty")) return "empty";
  return "out-of-range";
}

export default function ResultsList({ resolution, onExport }: ResultsListProps) {
  if (!resolution) {
    return (
      <div className="results-empty">
        <p>Submit a code snippet to see resolved function calls here.</p>
      </div>
    );
  }

  if (resolution.matches.length === 0) {
    return (
      <div className="results-empty">
        <p>No indirect calls found in the code snippet.</p>
      </div>
    );
  }

  return (
    <div className="results-list">
      <div className="results-header">
        <h2>
          Resolution results{" "}
          <span className="match-count">{resolution.matches.length} match(es)</span>
        </h2>
        <button
          type="button"
          className="btn btn-secondary"
          onClick={() => onExport(resolution)}
          aria-label="Export resolution results as JSON"
        >
          Export JSON
        </button>
      </div>

      <div className="match-table">
        <table>
          <thead>
            <tr>
              <th>Line</th>
              <th>Col</th>
              <th>Expression</th>
              <th>Slot #</th>
              <th>Resolved function</th>
              <th>Status</th>
              <th>Note</th>
            </tr>
          </thead>
          <tbody>
            {resolution.matches.map((m, i) => {
              const status = statusForMatch(m);
              return (
                <tr key={i} className={`status-${status}`}>
                  <td>{m.line}</td>
                  <td>{m.column}</td>
                  <td>
                    <code>{m.expression}</code>
                  </td>
                  <td>{m.slot_index}</td>
                  <td>
                    {m.resolved_function ? (
                      <code className="resolved-fn">{m.resolved_function}</code>
                    ) : (
                      <em className="unknown">unknown</em>
                    )}
                  </td>
                  <td>
                    <span className={`badge badge-${status}`}>
                      {m.resolved_function ? "resolved" : status}
                    </span>
                  </td>
                  <td className="note">{m.note}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export type { ResultsListProps };