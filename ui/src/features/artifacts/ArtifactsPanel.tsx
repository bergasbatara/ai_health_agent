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
} from "../../types/api";
import { useEffect, useState } from "react";
import { getErrorMessage, usePolling } from "../../lib";

import { DraftPanel } from "./DraftPanel";
import { EvidencePanel } from "./EvidencePanel";
import { FactsPanel } from "./FactsPanel";
import { PolicyMatchPanel } from "./PolicyMatchPanel";

interface ArtifactsPanelProps {
  workflowId: string | null;
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

const ARTIFACT_POLL_INTERVAL_MS = 5000;

export function ArtifactsPanel({ workflowId }: ArtifactsPanelProps) {
  const [artifacts, setArtifacts] = useState<ArtifactState>(initialState);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
    ARTIFACT_POLL_INTERVAL_MS,
    Boolean(workflowId),
  );

  return (
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
  );
}
