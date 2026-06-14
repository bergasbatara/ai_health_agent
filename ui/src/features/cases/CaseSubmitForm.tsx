import { useState } from "react";

import { submitCase } from "../../api/client";
import type { CaseSummaryResponse, SubmitCaseRequest } from "../../types/api";

interface CaseSubmitFormProps {
  onSubmitted: (workflow: CaseSummaryResponse) => void;
}

const initialPayload: SubmitCaseRequest = {
  case_path: "tmp/case-001.json",
  data_dir: "data",
  use_mock_crews: true,
  top_k: 5,
  model: "",
};

export function CaseSubmitForm({ onSubmitted }: CaseSubmitFormProps) {
  const [payload, setPayload] = useState<SubmitCaseRequest>(initialPayload);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSubmitting(true);
    setError(null);
    try {
      const result = await submitCase({
        ...payload,
        model: payload.model?.trim() ? payload.model : null,
      });
      onSubmitted(result.workflow);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Failed to submit case.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form className="case-submit-form" onSubmit={handleSubmit}>
      <div className="field-grid">
        <label className="field">
          <span>Case Path</span>
          <input
            value={payload.case_path}
            onChange={(event) => setPayload((current) => ({ ...current, case_path: event.target.value }))}
            placeholder="tmp/case-001.json"
            required
          />
        </label>

        <label className="field">
          <span>Data Directory</span>
          <input
            value={payload.data_dir ?? "data"}
            onChange={(event) => setPayload((current) => ({ ...current, data_dir: event.target.value }))}
            placeholder="data"
            required
          />
        </label>

        <label className="field">
          <span>Top K</span>
          <input
            type="number"
            min={1}
            max={50}
            value={payload.top_k ?? 5}
            onChange={(event) =>
              setPayload((current) => ({
                ...current,
                top_k: Number(event.target.value),
              }))
            }
          />
        </label>

        <label className="field">
          <span>Model</span>
          <input
            value={payload.model ?? ""}
            onChange={(event) => setPayload((current) => ({ ...current, model: event.target.value }))}
            placeholder="gpt-4o-mini"
            disabled={payload.use_mock_crews}
          />
        </label>
      </div>

      <label className="toggle-row">
        <input
          type="checkbox"
          checked={Boolean(payload.use_mock_crews)}
          onChange={(event) =>
            setPayload((current) => ({
              ...current,
              use_mock_crews: event.target.checked,
            }))
          }
        />
        <span>Use mock crews for local demo mode</span>
      </label>

      <div className="form-actions">
        <button className="primary-button" type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Submitting..." : "Submit Case"}
        </button>
        {error ? <p className="error-text">{error}</p> : null}
      </div>
    </form>
  );
}
