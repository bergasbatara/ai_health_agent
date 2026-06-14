import type { PolicyEvidenceResponse } from "../../types/api";

interface EvidencePanelProps {
  data: PolicyEvidenceResponse | null;
  loading: boolean;
  error: string | null;
  emptyMessage: string;
}

export function EvidencePanel({ data, loading, error, emptyMessage }: EvidencePanelProps) {
  const evidence = data?.retrieval_result?.evidence ?? [];
  const queryText = data?.retrieval_result?.query.query_text;

  return (
    <article className="panel artifact-panel">
      <div className="panel-header">
        <h2>Evidence</h2>
        <span className="badge badge-idle">{evidence.length}</span>
      </div>

      {loading ? <p className="meta">Loading policy evidence...</p> : null}
      {!loading && error ? <p className="error-text">{error}</p> : null}
      {!loading && !error && !data?.retrieval_result ? <p className="meta">{emptyMessage}</p> : null}

      {!loading && !error && data?.retrieval_result ? (
        <>
          <p className="meta artifact-query">{queryText}</p>
          {evidence.length === 0 ? <p className="meta">No evidence chunks were returned.</p> : null}
          {evidence.length > 0 ? (
            <ul className="artifact-list">
              {evidence.map((item) => (
                <li key={item.evidence_id} className="artifact-list-item">
                  <strong>{item.document_id}</strong>
                  <p>{item.citation_text}</p>
                </li>
              ))}
            </ul>
          ) : null}
        </>
      ) : null}
    </article>
  );
}
