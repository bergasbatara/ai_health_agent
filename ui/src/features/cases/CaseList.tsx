import type { CaseSummaryResponse } from "../../types/api";

interface CaseListProps {
  cases: CaseSummaryResponse[];
  loading: boolean;
  error: string | null;
  selectedWorkflowId: string | null;
  onSelect: (workflowId: string) => void;
}

export function CaseList({
  cases,
  loading,
  error,
  selectedWorkflowId,
  onSelect,
}: CaseListProps) {
  if (loading) {
    return <p className="meta">Loading dashboard data...</p>;
  }

  if (error) {
    return <p className="error-text">{error}</p>;
  }

  if (cases.length === 0) {
    return <p className="meta">No cases submitted yet.</p>;
  }

  return (
    <ul className="case-list">
      {cases.map((item) => {
        const isSelected = item.workflow_id === selectedWorkflowId;
        return (
          <li key={item.workflow_id}>
            <button
              type="button"
              className={`case-row-button ${isSelected ? "case-row-button-selected" : ""}`}
              onClick={() => onSelect(item.workflow_id)}
            >
              <div className="case-row">
                <div>
                  <strong>{item.case_id ?? item.workflow_id}</strong>
                  <p>{item.workflow_id}</p>
                </div>
                <span className={`badge badge-${item.status.replaceAll("_", "-")}`}>{item.status}</span>
              </div>
            </button>
          </li>
        );
      })}
    </ul>
  );
}
