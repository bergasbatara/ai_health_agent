import type { CaseSummaryResponse } from "../../types/api";

interface CaseStatusCardProps {
  selectedCase: CaseSummaryResponse | null;
}

export function CaseStatusCard({ selectedCase }: CaseStatusCardProps) {
  if (!selectedCase) {
    return (
      <article className="panel">
        <div className="panel-header">
          <h2>Selected Case</h2>
        </div>
        <p className="meta">Select a case to inspect its current workflow status.</p>
      </article>
    );
  }

  return (
    <article className="panel">
      <div className="panel-header">
        <h2>Selected Case</h2>
        <span className={`badge badge-${selectedCase.status.replaceAll("_", "-")}`}>{selectedCase.status}</span>
      </div>
      <dl className="detail-list">
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
        <div>
          <dt>Issues</dt>
          <dd>{selectedCase.issue_count}</dd>
        </div>
        <div>
          <dt>Failures</dt>
          <dd>{selectedCase.failure_count}</dd>
        </div>
      </dl>
    </article>
  );
}
