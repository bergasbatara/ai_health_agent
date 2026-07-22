import type {
  CaseChatRequest,
  CaseChatResponse,
  CaseSummaryResponse,
  DraftOutputResponse,
  ErrorEnvelope,
  ExtractedFactsResponse,
  HealthResponse,
  PolicyEvidenceResponse,
  PolicyMatchResponse,
  SubmitCaseRequest,
  SubmitCaseResponse,
} from "../types/api";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  if (!response.ok) {
    let detail = `Request failed with status ${response.status}`;
    try {
      const payload = (await response.json()) as ErrorEnvelope;
      detail = payload.error?.detail ?? detail;
    } catch {
      // Keep generic fallback when no JSON body exists.
    }
    throw new Error(detail);
  }

  return (await response.json()) as T;
}

export function getHealth(): Promise<HealthResponse> {
  return requestJson<HealthResponse>("/health");
}

export function listCases(): Promise<CaseSummaryResponse[]> {
  return requestJson<CaseSummaryResponse[]>("/cases");
}

export function submitCase(payload: SubmitCaseRequest): Promise<SubmitCaseResponse> {
  return requestJson<SubmitCaseResponse>("/cases", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getCaseStatus(workflowId: string): Promise<CaseSummaryResponse> {
  return requestJson<CaseSummaryResponse>(`/cases/${workflowId}`);
}

export function getExtractedFacts(workflowId: string): Promise<ExtractedFactsResponse> {
  return requestJson<ExtractedFactsResponse>(`/cases/${workflowId}/facts`);
}

export function getPolicyEvidence(workflowId: string): Promise<PolicyEvidenceResponse> {
  return requestJson<PolicyEvidenceResponse>(`/cases/${workflowId}/evidence`);
}

export function getPolicyMatch(workflowId: string): Promise<PolicyMatchResponse> {
  return requestJson<PolicyMatchResponse>(`/cases/${workflowId}/policy-match`);
}

export function getDraftOutput(workflowId: string): Promise<DraftOutputResponse> {
  return requestJson<DraftOutputResponse>(`/cases/${workflowId}/draft`);
}

export function chatWithCase(workflowId: string, payload: CaseChatRequest): Promise<CaseChatResponse> {
  return requestJson<CaseChatResponse>(`/cases/${workflowId}/chat`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
