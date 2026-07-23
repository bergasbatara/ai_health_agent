import { useState } from "react";

import { chatWithCase, getPolicyEvidence } from "../../api/client";
import { PanelCard, StatusBadge } from "../../components";
import { getErrorMessage } from "../../lib";
import type { CaseChatResponse, PolicyEvidence, PolicyEvidenceResponse } from "../../types/api";

interface ChatPanelProps {
  workflowId: string | null;
}

interface ChatHistoryEntry {
  question: string;
  response: CaseChatResponse;
  sources: PolicyEvidence[];
}

interface StructuredAnswerSection {
  title: string;
  body: string;
}

const STARTER_PROMPTS = [
  "Summarize this case for a human reviewer.",
  "Why does this case appear to meet policy criteria?",
  "What evidence supports the current recommendation?",
  "What is missing or still ambiguous in this case?",
];

function parseStructuredSections(text: string): StructuredAnswerSection[] {
  const lines = text.split("\n").map((line) => line.trim()).filter(Boolean);
  const sections: StructuredAnswerSection[] = [];
  let currentTitle = "Response";
  let currentBody: string[] = [];

  function flushSection() {
    if (currentBody.length === 0) {
      return;
    }
    sections.push({
      title: currentTitle,
      body: currentBody.join(" "),
    });
    currentBody = [];
  }

  for (const line of lines) {
    const match = /^(Bottom line|Evidence|Missing \/ ambiguous|Draft readiness):\s*(.*)$/i.exec(line);
    if (match) {
      flushSection();
      currentTitle = match[1];
      if (match[2]) {
        currentBody.push(match[2]);
      }
      continue;
    }
    currentBody.push(line);
  }

  flushSection();
  return sections;
}

export function ChatPanel({ workflowId }: ChatPanelProps) {
  const [message, setMessage] = useState("");
  const [history, setHistory] = useState<ChatHistoryEntry[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function submitMessage(nextMessage: string) {
    if (!workflowId) {
      return;
    }

    setIsSubmitting(true);
    setError(null);
    try {
      const [chatResponse, evidenceResponse] = await Promise.all([
        chatWithCase(workflowId, { message: nextMessage }),
        getPolicyEvidence(workflowId).catch(() => null as PolicyEvidenceResponse | null),
      ]);
      const sources = evidenceResponse?.retrieval_result?.evidence?.slice(0, 3) ?? [];
      setHistory((current) => [
        ...current,
        {
          question: nextMessage,
          response: chatResponse,
          sources,
        },
      ]);
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

  const latestResponse = history.at(-1)?.response ?? null;

  return (
    <PanelCard
      title="Case Chat"
      badge={<StatusBadge value={workflowId ? latestResponse?.status ?? "ready" : "idle"} tone={workflowId ? undefined : "idle"} />}
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
              <h2>Conversation</h2>
              <StatusBadge
                value={latestResponse?.chat_response.model.display_name ?? "waiting"}
                tone={latestResponse ? "ok" : "idle"}
              />
            </div>
            {history.length === 0 ? (
              <p className="meta">No chat response yet.</p>
            ) : (
              <div className="chat-history">
                {history.map((entry, index) => {
                  const assistantText = entry.response.chat_response.message.content
                    .map((block) => block.text)
                    .filter((value): value is string => Boolean(value))
                    .join("\n\n");
                  const sections = parseStructuredSections(assistantText);
                  return (
                    <article key={`${entry.response.workflow_id}-${index}`} className="chat-turn">
                      <div className="chat-bubble chat-bubble-user">
                        <p className="chat-turn-label">Reviewer</p>
                        <p className="chat-response-text">{entry.question}</p>
                      </div>
                      <div className="chat-bubble chat-bubble-assistant">
                        <div className="chat-turn-header">
                          <p className="chat-turn-label">Assistant</p>
                          <StatusBadge value={entry.response.status} />
                        </div>
                        <div className="chat-sections">
                          {sections.map((section) => (
                            <section key={`${entry.response.workflow_id}-${index}-${section.title}`} className="chat-section-block">
                              <h3>{section.title}</h3>
                              <p className="chat-response-text">{section.body}</p>
                            </section>
                          ))}
                        </div>
                        {entry.sources.length > 0 ? (
                          <div className="chat-sources">
                            <p className="chat-turn-label">Sources used</p>
                            <ul className="artifact-list">
                              {entry.sources.map((source) => (
                                <li key={source.evidence_id} className="artifact-list-item">
                                  <strong>{source.document_id}</strong>
                                  <p>
                                    {source.section_label ? `${source.section_label} · ` : ""}
                                    {source.page_number ? `Page ${source.page_number}` : "Page unavailable"}
                                  </p>
                                </li>
                              ))}
                            </ul>
                          </div>
                        ) : null}
                        <p className="meta">Tokens: {entry.response.chat_response.usage.total_tokens} total</p>
                      </div>
                    </article>
                  );
                })}
              </div>
            )}
          </div>
        </>
      )}
    </PanelCard>
  );
}
