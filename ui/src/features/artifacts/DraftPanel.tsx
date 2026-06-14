import type { DraftOutputResponse } from "../../types/api";

interface DraftPanelProps {
  data: DraftOutputResponse | null;
  loading: boolean;
  error: string | null;
  emptyMessage: string;
}

export function DraftPanel({ data, loading, error, emptyMessage }: DraftPanelProps) {
  const draft = data?.prior_auth_draft;

  return (
    <article className="panel artifact-panel">
      <div className="panel-header">
        <h2>Draft</h2>
        <span className={`badge ${draft ? `badge-${draft.review_status.replaceAll("_", "-")}` : "badge-idle"}`}>
          {draft?.review_status ?? "empty"}
        </span>
      </div>

      {loading ? <p className="meta">Loading draft output...</p> : null}
      {!loading && error ? <p className="error-text">{error}</p> : null}
      {!loading && !error && !draft ? <p className="meta">{emptyMessage}</p> : null}

      {!loading && !error && draft ? (
        <>
          <p className="meta artifact-query">{draft.reviewer_summary}</p>
          <dl className="detail-list">
            <div>
              <dt>Form Fields</dt>
              <dd>{draft.form_fields.length}</dd>
            </div>
            <div>
              <dt>Missing Requirements</dt>
              <dd>{draft.missing_requirements.length}</dd>
            </div>
            <div>
              <dt>Unresolved Issues</dt>
              <dd>{draft.unresolved_issues.length}</dd>
            </div>
            <div>
              <dt>Risk Flags</dt>
              <dd>{draft.risk_flags.length}</dd>
            </div>
          </dl>
        </>
      ) : null}
    </article>
  );
}
