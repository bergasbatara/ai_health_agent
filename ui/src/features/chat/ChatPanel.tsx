import { useState } from "react";

import { chatWithCase } from "../../api/client";
import { PanelCard, StatusBadge } from "../../components";
import { getErrorMessage } from "../../lib";
import type { CaseChatResponse } from "../../types/api";

interface ChatPanelProps {
  workflowId: string | null;
}

const STARTER_PROMPTS = [
  "Summarize this case for a human reviewer.",
  "Why does this case appear to meet policy criteria?",
  "What evidence supports the current recommendation?",
  "What is missing or still ambiguous in this case?",
];

export function ChatPanel({ workflowId }: ChatPanelProps) {
  const [message, setMessage] = useState("");
  const [response, setResponse] = useState<CaseChatResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function submitMessage(nextMessage: string) {
    if (!workflowId) {
      return;
    }

    setIsSubmitting(true);
    setError(null);
    try {
      const chatResponse = await chatWithCase(workflowId, { message: nextMessage });
      setResponse(chatResponse);
    } catch (caught) {
      setError(getErrorMessage(caught, "Failed to get chat response."));
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = message.trim();
    if (!trimmed || !workflowId) {
      return;
    }

    await submitMessage(trimmed);
  }

  const assistantText = response?.chat_response.message.content
    .map((block) => block.text)
    .filter((value): value is string => Boolean(value))
    .join("\n\n");

  return (
    <PanelCard
      title="Case Chat"
      badge={<StatusBadge value={workflowId ? response?.status ?? "ready" : "idle"} tone={workflowId ? undefined : "idle"} />}
      className="chat-panel"
    >
      {!workflowId ? (
        <p className="meta">Select a case to ask grounded questions about its facts, evidence, and draft.</p>
      ) : (
        <>
          <p className="meta">
            Ask case-specific questions. The assistant should answer only from workflow artifacts and cited evidence.
          </p>

          <div className="chat-starters">
            {STARTER_PROMPTS.map((prompt) => (
              <button
                key={prompt}
                type="button"
                className="secondary-button"
                disabled={isSubmitting}
                onClick={() => {
                  setMessage(prompt);
                  void submitMessage(prompt);
                }}
              >
                {prompt}
              </button>
            ))}
          </div>

          <form className="chat-form" onSubmit={handleSubmit}>
            <label className="field">
              <span>Reviewer Question</span>
              <textarea
                className="chat-textarea"
                value={message}
                onChange={(event) => setMessage(event.target.value)}
                placeholder="Ask why this case was approved, what evidence supports it, or what is missing."
                rows={5}
                disabled={isSubmitting}
              />
            </label>
            <div className="form-actions">
              <button className="primary-button" type="submit" disabled={isSubmitting || message.trim().length === 0}>
                {isSubmitting ? "Asking..." : "Ask Chatbot"}
              </button>
              {error ? <p className="error-text">{error}</p> : null}
            </div>
          </form>

          <div className="chat-response">
            <div className="panel-header">
              <h2>Assistant Answer</h2>
              <StatusBadge value={response?.chat_response.model.display_name ?? "waiting"} tone={response ? "ok" : "idle"} />
            </div>
            {assistantText ? <p className="chat-response-text">{assistantText}</p> : <p className="meta">No chat response yet.</p>}
            {response ? (
              <p className="meta">
                Tokens: {response.chat_response.usage.total_tokens} total
              </p>
            ) : null}
          </div>
        </>
      )}
    </PanelCard>
  );
}
