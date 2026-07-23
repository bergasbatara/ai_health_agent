import { useEffect, useState } from "react";

import { getHealth, listCases } from "../api/client";
import { PanelCard, StatusBadge } from "../components";
import { ChatPanel } from "../features/chat";
import { CaseList, CaseSubmitForm } from "../features/cases";
import { formatRelativeTime, getErrorMessage, usePolling } from "../lib";
import type { CaseSummaryResponse, HealthResponse, WorkflowRunStatus } from "../types/api";

const ACTIVE_DASHBOARD_POLL_INTERVAL_MS = 5000;
const IDLE_DASHBOARD_POLL_INTERVAL_MS = 30000;

function isActiveWorkflow(status: WorkflowRunStatus): boolean {
  return status === "not_started" || status === "running";
}

export function DashboardPage() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [cases, setCases] = useState<CaseSummaryResponse[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedWorkflowId, setSelectedWorkflowId] = useState<string | null>(null);
  const [lastUpdatedAt, setLastUpdatedAt] = useState<Date | null>(null);

  async function loadDashboard(showLoading: boolean) {
    if (showLoading) {
      setLoading(true);
    }

    try {
      const [healthResponse, casesResponse] = await Promise.all([getHealth(), listCases()]);
      setHealth(healthResponse);
      setCases(casesResponse);
      setError(null);
      setLastUpdatedAt(new Date());
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

  const selectedCase = cases.find((item) => item.workflow_id === selectedWorkflowId) ?? null;
  const dashboardPollIntervalMs = cases.some((item) => isActiveWorkflow(item.status))
    ? ACTIVE_DASHBOARD_POLL_INTERVAL_MS
    : IDLE_DASHBOARD_POLL_INTERVAL_MS;
  const dashboardRefreshLabel = cases.some((item) => isActiveWorkflow(item.status))
    ? "Live refresh every 5s"
    : "Background refresh every 30s";

  usePolling(() => {
    void loadDashboard(false);
  }, dashboardPollIntervalMs);

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
          Submit a case, select it, and use a grounded chatbot to inspect policy reasoning,
          evidence, and draft readiness from backend workflow artifacts.
        </p>
        <div className="refresh-status">
          <span className="refresh-indicator" aria-hidden="true" />
          <span>{dashboardRefreshLabel}</span>
          <span>{formatRelativeTime(lastUpdatedAt)}</span>
        </div>
      </section>

      <section className="panel-grid">
        <PanelCard title="Submit Case">
          <CaseSubmitForm onSubmitted={handleCaseSubmitted} />
        </PanelCard>

        <PanelCard
          title="Pick Case"
          badge={<StatusBadge value={selectedCase?.status ?? cases.length} tone={selectedCase ? undefined : "idle"} />}
        >
          <CaseList
            cases={cases}
            loading={loading}
            error={error}
            selectedWorkflowId={selectedWorkflowId}
            onSelect={setSelectedWorkflowId}
          />
        </PanelCard>
      </section>

      <section className="chat-section">
        <div className="section-heading">
          <h2>Chatbot</h2>
          <p className="meta">
            {selectedCase
              ? `Chatting with ${selectedCase.case_id ?? selectedCase.workflow_id}. Answers are grounded in the selected case workflow artifacts.`
              : "Select a case to start a grounded conversation over its workflow artifacts."}
          </p>
        </div>
        <PanelCard
          title="Selected Case"
          badge={<StatusBadge value={selectedCase?.status ?? "idle"} tone={selectedCase ? undefined : "idle"} />}
        >
          {selectedCase ? (
            <dl className="detail-list detail-list-compact">
              <div>
                <dt>Case ID</dt>
                <dd>{selectedCase.case_id ?? "Unknown"}</dd>
              </div>
              <div>
                <dt>Workflow ID</dt>
                <dd>{selectedCase.workflow_id}</dd>
              </div>
              <div>
                <dt>Current Step</dt>
                <dd>{selectedCase.current_step ?? "Not available"}</dd>
              </div>
            </dl>
          ) : (
            <p className="meta">No case selected yet.</p>
          )}
        </PanelCard>
        <ChatPanel workflowId={selectedWorkflowId} />
      </section>
    </main>
  );
}
