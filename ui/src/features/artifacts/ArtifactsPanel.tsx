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

export function ArtifactsPanel({ workflowId }: ArtifactsPanelProps) {
  const [artifacts, setArtifacts] = useState<ArtifactState>(initialState);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!workflowId) {
      setArtifacts(initialState);
      setError(null);
      setLoading(false);
      return;
    }

    async function loadArtifacts() {
      setLoading(true);
      setError(null);
      try {
        const [facts, evidence, policyMatch, draft] = await Promise.all([
          getExtractedFacts(workflowId),
          getPolicyEvidence(workflowId),
          getPolicyMatch(workflowId),
          getDraftOutput(workflowId),
        ]);
        setArtifacts({ facts, evidence, policyMatch, draft });
      } catch (caught) {
        const message = caught instanceof Error ? caught.message : "Failed to load artifact panels.";
        setError(message);
      } finally {
        setLoading(false);
      }
    }

    void loadArtifacts();
  }, [workflowId]);

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
