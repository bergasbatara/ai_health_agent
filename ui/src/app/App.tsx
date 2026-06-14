import { useEffect, useState } from "react";

import { getHealth, listCases } from "../api/client";
import type { CaseSummaryResponse, HealthResponse } from "../types/api";

export function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [cases, setCases] = useState<CaseSummaryResponse[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadDashboard() {
      try {
        const [healthResponse, casesResponse] = await Promise.all([getHealth(), listCases()]);
        setHealth(healthResponse);
        setCases(casesResponse);
      } catch (caught) {
        const message = caught instanceof Error ? caught.message : "Unknown API error";
        setError(message);
      } finally {
        setLoading(false);
      }
    }

    void loadDashboard();
  }, []);

  return (
    <main className="app-shell">
      <section className="hero">
        <p className="eyebrow">Prior Authorization Review</p>
        <h1>AI Health Agent Dashboard</h1>
        <p className="lede">
          Thin frontend over the review API. This UI only consumes backend responses and does not
          perform policy or clinical reasoning.
        </p>
      </section>

      <section className="panel-grid">
        <article className="panel">
          <div className="panel-header">
            <h2>API Health</h2>
            <span className={`badge ${health?.status === "ok" ? "badge-ok" : "badge-idle"}`}>
              {health?.status ?? "unknown"}
            </span>
          </div>
          <p className="meta">{health?.service ?? "No response yet"}</p>
        </article>

        <article className="panel">
          <div className="panel-header">
            <h2>Cases</h2>
            <span className="badge badge-idle">{cases.length}</span>
          </div>

          {loading ? <p className="meta">Loading dashboard data...</p> : null}
          {error ? <p className="error-text">{error}</p> : null}

          {!loading && !error && cases.length === 0 ? (
            <p className="meta">No cases submitted yet.</p>
          ) : null}

          {!loading && !error && cases.length > 0 ? (
            <ul className="case-list">
              {cases.map((item) => (
                <li key={item.workflow_id} className="case-row">
                  <div>
                    <strong>{item.case_id ?? item.workflow_id}</strong>
                    <p>{item.workflow_id}</p>
                  </div>
                  <span className={`badge badge-${item.status.replaceAll("_", "-")}`}>{item.status}</span>
                </li>
              ))}
            </ul>
          ) : null}
        </article>
      </section>
    </main>
  );
}
