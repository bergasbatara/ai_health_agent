import { useEffect, useState } from "react";

import { getHealth, listCases } from "../api/client";
import { ArtifactsPanel } from "../features/artifacts";
import { CaseList, CaseStatusCard, CaseSubmitForm } from "../features/cases";
import type { CaseSummaryResponse, HealthResponse } from "../types/api";

export function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [cases, setCases] = useState<CaseSummaryResponse[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedWorkflowId, setSelectedWorkflowId] = useState<string | null>(null);

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

  const selectedCase = cases.find((item) => item.workflow_id === selectedWorkflowId) ?? null;

  function handleCaseSubmitted(workflow: CaseSummaryResponse) {
    setCases((current) => {
      const next = [workflow, ...current.filter((item) => item.workflow_id !== workflow.workflow_id)];
      return next;
    });
    setSelectedWorkflowId(workflow.workflow_id);
  }

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
            <h2>Submit Case</h2>
          </div>
          <CaseSubmitForm onSubmitted={handleCaseSubmitted} />
        </article>

        <article className="panel">
          <div className="panel-header">
            <h2>Cases</h2>
            <span className="badge badge-idle">{cases.length}</span>
          </div>
          <CaseList
            cases={cases}
            loading={loading}
            error={error}
            selectedWorkflowId={selectedWorkflowId}
            onSelect={setSelectedWorkflowId}
          />
        </article>

        <CaseStatusCard selectedCase={selectedCase} />
      </section>

      <section className="artifact-section">
        <div className="section-heading">
          <h2>Review Artifacts</h2>
          <p className="meta">
            The dashboard reads facts, evidence, policy match, and draft output strictly from API responses.
          </p>
        </div>
        <ArtifactsPanel workflowId={selectedWorkflowId} />
      </section>
    </main>
  );
}
