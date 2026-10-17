import { useEffect, useState } from "react";
import ResolverDashboard from "./pages/ResolverDashboard";
import type { HealthCheck, VersionInfo } from "./api/client";
import { api } from "./api/client";
import "./styles.css";

function App() {
  const [health, setHealth] = useState<HealthCheck | null>(null);
  const [version, setVersion] = useState<VersionInfo | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);

  useEffect(() => {
    api
      .health()
      .then(setHealth)
      .catch(() => setHealthError("Backend unreachable"));
    api.version().then(setVersion).catch(() => {});
  }, []);

  const backendOk = health?.status === "ok";

  return (
    <div className="app">
      <header className="app-header">
        <h1>
          Lumen Studio{" "}
          <span className="subtitle">Resolve Indirect Vtable Calls</span>
        </h1>
        {backendOk && version && (
          <p className="meta">
            v{version.version} · {version.demo_mode ? "demo mode" : "prod mode"}
          </p>
        )}
        {!backendOk && (
          <p className="meta error">
            ⚠ {healthError || "Waiting for backend…"}
          </p>
        )}
      </header>

      {!backendOk && (
        <div className="banner error-banner">
          Backend is not reachable. Start it with{" "}
          <code>PYTHONPATH=backend uvicorn app.main:app --port 8000</code>.
        </div>
      )}

      <main className={backendOk ? "ready" : "dimmed"}>
        <ResolverDashboard />
      </main>

      <footer className="app-footer">
        <p>
          Ryan Vo | AI &amp; Machine Learning — reverse-engineering assistant
          for resolving indirect function calls in decompiled binaries.
        </p>
      </footer>
    </div>
  );
}

export default App;