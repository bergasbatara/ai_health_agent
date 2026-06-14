import { PanelCard, StatusBadge } from "../../components";
import type { ExtractedFactsResponse } from "../../types/api";

interface FactsPanelProps {
  data: ExtractedFactsResponse | null;
  loading: boolean;
  error: string | null;
  emptyMessage: string;
}

export function FactsPanel({ data, loading, error, emptyMessage }: FactsPanelProps) {
  const facts = data?.extracted_facts;

  return (
    <PanelCard
      title="Facts"
      badge={<StatusBadge value={facts ? "loaded" : "empty"} tone="idle" />}
      className="artifact-panel"
    >
      {loading ? <p className="meta">Loading extracted facts...</p> : null}
      {!loading && error ? <p className="error-text">{error}</p> : null}
      {!loading && !error && !facts ? <p className="meta">{emptyMessage}</p> : null}

      {!loading && !error && facts ? (
        <dl className="detail-list">
          <div>
            <dt>Modality</dt>
            <dd>{facts.requested_modality}</dd>
          </div>
          <div>
            <dt>Body Region</dt>
            <dd>{facts.requested_body_region}</dd>
          </div>
          <div>
            <dt>Laterality</dt>
            <dd>{facts.requested_laterality}</dd>
          </div>
          <div>
            <dt>Symptom Duration</dt>
            <dd>{facts.symptom_duration_weeks ?? "Unknown"}</dd>
          </div>
          <div>
            <dt>Conservative Therapy</dt>
            <dd>{facts.conservative_therapy_completed}</dd>
          </div>
          <div>
            <dt>Prior Imaging</dt>
            <dd>{facts.prior_imaging_completed}</dd>
          </div>
          <div>
            <dt>Reason For Order</dt>
            <dd>{facts.reason_for_order ?? "Not provided"}</dd>
          </div>
        </dl>
      ) : null}
    </PanelCard>
  );
}
