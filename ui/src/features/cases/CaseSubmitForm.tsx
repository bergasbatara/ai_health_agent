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

const CASE_OPTIONS = Array.from({ length: 15 }, (_, index) => {
  const caseNumber = String(index + 1).padStart(3, "0");
  return `tmp/case-${caseNumber}.json`;
});

const CUSTOM_CASE_OPTION = "__custom__";

export function CaseSubmitForm({ onSubmitted }: CaseSubmitFormProps) {
  const [payload, setPayload] = useState<SubmitCaseRequest>(initialPayload);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedCasePath, setSelectedCasePath] = useState<string>(
    CASE_OPTIONS.includes(initialPayload.case_path) ? initialPayload.case_path : CUSTOM_CASE_OPTION,
  );

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
          <span>Case Selection</span>
          <select
            value={selectedCasePath}
            onChange={(event) => {
              const nextValue = event.target.value;
              setSelectedCasePath(nextValue);
              if (nextValue !== CUSTOM_CASE_OPTION) {
                setPayload((current) => ({ ...current, case_path: nextValue }));
              }
            }}
          >
            {CASE_OPTIONS.map((casePath) => (
              <option key={casePath} value={casePath}>
                {casePath.replace("tmp/", "")}
              </option>
            ))}
            <option value={CUSTOM_CASE_OPTION}>Custom path...</option>
          </select>
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
          <span>Workflow Agent Model</span>
          <input
            value={payload.model ?? ""}
            onChange={(event) => setPayload((current) => ({ ...current, model: event.target.value }))}
            placeholder="Optional non-mock workflow model"
            disabled={payload.use_mock_crews}
          />
        </label>
      </div>

      {selectedCasePath === CUSTOM_CASE_OPTION ? (
        <label className="field">
          <span>Custom Case Path</span>
          <input
            value={payload.case_path}
            onChange={(event) => setPayload((current) => ({ ...current, case_path: event.target.value }))}
            placeholder="tmp/case-001.json"
            required
          />
        </label>
      ) : null}

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
      <p className="meta">
        Chatbot model is configured separately on the backend via SiliconFlow environment variables.
      </p>

      <div className="form-actions">
        <button className="primary-button" type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Submitting..." : "Submit Case"}
        </button>
        {error ? <p className="error-text">{error}</p> : null}
      </div>
    </form>
  );
}
