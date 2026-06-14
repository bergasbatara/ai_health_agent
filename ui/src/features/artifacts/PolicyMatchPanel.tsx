import { PanelCard, StatusBadge } from "../../components";
import type { PolicyMatchResponse } from "../../types/api";

interface PolicyMatchPanelProps {
  data: PolicyMatchResponse | null;
  loading: boolean;
  error: string | null;
  emptyMessage: string;
}

export function PolicyMatchPanel({ data, loading, error, emptyMessage }: PolicyMatchPanelProps) {
  const match = data?.policy_match_result;
  const criteria = match?.criteria ?? [];

  return (
    <PanelCard title="Policy Match" badge={<StatusBadge value={criteria.length} />} className="artifact-panel">
      {loading ? <p className="meta">Loading policy match result...</p> : null}
      {!loading && error ? <p className="error-text">{error}</p> : null}
      {!loading && !error && !match ? <p className="meta">{emptyMessage}</p> : null}

      {!loading && !error && match ? (
        <>
          <p className="meta artifact-query">{match.policy_requirements_summary}</p>
          {criteria.length > 0 ? (
            <ul className="artifact-list">
              {criteria.map((criterion, index) => (
                <li key={`${String(criterion.criterion_key ?? "criterion")}-${index}`} className="artifact-list-item">
                  <strong>{String(criterion.display_name ?? criterion.criterion_key ?? "Criterion")}</strong>
                  <p>Status: {String(criterion.status ?? "unknown")}</p>
                </li>
              ))}
            </ul>
          ) : (
            <p className="meta">No normalized criteria were returned.</p>
          )}
        </>
      ) : null}
    </PanelCard>
  );
}
