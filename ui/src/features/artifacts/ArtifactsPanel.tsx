import {
  getDraftOutput,
  getExtractedFacts,
  getPolicyEvidence,
  getPolicyMatch,
} from "../../api/client";
import type {
  DraftOutputResponse,
  ExtractedFactsResponse,
  PolicyEvidenceResponse,
  PolicyMatchResponse,
  WorkflowRunStatus,
} from "../../types/api";
import { useEffect, useState } from "react";
import { formatRelativeTime, getErrorMessage, usePolling } from "../../lib";

import { DraftPanel } from "./DraftPanel";
import { EvidencePanel } from "./EvidencePanel";
import { FactsPanel } from "./FactsPanel";
import { PolicyMatchPanel } from "./PolicyMatchPanel";

interface ArtifactsPanelProps {
  workflowId: string | null;
  workflowStatus: WorkflowRunStatus | null;
}

interface ArtifactState {
  facts: ExtractedFactsResponse | null;
  evidence: PolicyEvidenceResponse | null;
  policyMatch: PolicyMatchResponse | null;
  draft: DraftOutputResponse | null;
}

const initialState: ArtifactState = {
  facts: null,
  evidence: null,
  policyMatch: null,
  draft: null,
};

const ACTIVE_ARTIFACT_POLL_INTERVAL_MS = 4000;
const IDLE_ARTIFACT_POLL_INTERVAL_MS = 30000;

function isActiveWorkflow(status: WorkflowRunStatus | null): boolean {
  return status === "not_started" || status === "running";
}

export function ArtifactsPanel({ workflowId, workflowStatus }: ArtifactsPanelProps) {
  const [artifacts, setArtifacts] = useState<ArtifactState>(initialState);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdatedAt, setLastUpdatedAt] = useState<Date | null>(null);
  const artifactPollIntervalMs = isActiveWorkflow(workflowStatus)
    ? ACTIVE_ARTIFACT_POLL_INTERVAL_MS
    : IDLE_ARTIFACT_POLL_INTERVAL_MS;

  async function loadArtifacts(currentWorkflowId: string, showLoading: boolean) {
    if (showLoading) {
      setLoading(true);
    }

    try {
      const [facts, evidence, policyMatch, draft] = await Promise.all([
        getExtractedFacts(currentWorkflowId),
        getPolicyEvidence(currentWorkflowId),
        getPolicyMatch(currentWorkflowId),
        getDraftOutput(currentWorkflowId),
      ]);
      setArtifacts({ facts, evidence, policyMatch, draft });
      setError(null);
      setLastUpdatedAt(new Date());
    } catch (caught) {
      setError(getErrorMessage(caught, "Failed to load artifact panels."));
    } finally {
      if (showLoading) {
        setLoading(false);
      }
    }
  }

  useEffect(() => {
    if (!workflowId) {
      setArtifacts(initialState);
      setError(null);
      setLoading(false);
      setLastUpdatedAt(null);
      return;
    }

    void loadArtifacts(workflowId, true);
  }, [workflowId]);

  usePolling(
    () => {
      if (!workflowId) {
        return;
      }

      void loadArtifacts(workflowId, false);
    },
    artifactPollIntervalMs,
    Boolean(workflowId),
  );

  return (
    <>
      <div className="refresh-status">
        <span className="refresh-indicator" aria-hidden="true" />
        <span>{isActiveWorkflow(workflowStatus) ? "Artifact refresh every 4s" : "Artifact refresh every 30s"}</span>
        <span>{formatRelativeTime(lastUpdatedAt)}</span>
      </div>
      <section className="artifact-grid">
        <FactsPanel
          data={artifacts.facts}
          loading={loading}
          error={error}
          emptyMessage="Select a case to inspect extracted clinical facts."
        />
        <EvidencePanel
          data={artifacts.evidence}
          loading={loading}
          error={error}
          emptyMessage="Select a case to inspect retrieved policy evidence."
        />
        <PolicyMatchPanel
          data={artifacts.policyMatch}
          loading={loading}
          error={error}
          emptyMessage="Select a case to inspect normalized policy criteria."
        />
        <DraftPanel
          data={artifacts.draft}
          loading={loading}
          error={error}
          emptyMessage="Select a case to inspect the prior authorization draft."
        />
      </section>
    </>
  );
}
