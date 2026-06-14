import { useEffect, useState } from "react";

import { getHealth, listCases } from "../api/client";
import { PanelCard, StatusBadge } from "../components";
import { ArtifactsPanel } from "../features/artifacts";
import { CaseList, CaseStatusCard, CaseSubmitForm } from "../features/cases";
import { getErrorMessage, usePolling } from "../lib";
import type { CaseSummaryResponse, HealthResponse } from "../types/api";

const DASHBOARD_POLL_INTERVAL_MS = 10000;

export function DashboardPage() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [cases, setCases] = useState<CaseSummaryResponse[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedWorkflowId, setSelectedWorkflowId] = useState<string | null>(null);

  async function loadDashboard(showLoading: boolean) {
    if (showLoading) {
      setLoading(true);
    }

    try {
      const [healthResponse, casesResponse] = await Promise.all([getHealth(), listCases()]);
      setHealth(healthResponse);
      setCases(casesResponse);
      setError(null);
    } catch (caught) {
      setError(getErrorMessage(caught, "Unknown API error"));
    } finally {
      if (showLoading) {
        setLoading(false);
      }
    }
  }

  useEffect(() => {
    void loadDashboard(true);
  }, []);

  usePolling(() => {
    void loadDashboard(false);
  }, DASHBOARD_POLL_INTERVAL_MS);

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
        <PanelCard
          title="API Health"
          badge={<StatusBadge value={health?.status} tone={health?.status === "ok" ? "ok" : undefined} />}
        >
          <p className="meta">{health?.service ?? "No response yet"}</p>
        </PanelCard>

        <PanelCard title="Submit Case">
          <CaseSubmitForm onSubmitted={handleCaseSubmitted} />
        </PanelCard>

        <PanelCard title="Cases" badge={<StatusBadge value={cases.length} />}>
          <CaseList
            cases={cases}
            loading={loading}
            error={error}
            selectedWorkflowId={selectedWorkflowId}
            onSelect={setSelectedWorkflowId}
          />
        </PanelCard>

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
