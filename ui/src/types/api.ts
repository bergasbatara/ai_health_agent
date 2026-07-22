export type WorkflowRunStatus =
  | "not_started"
  | "running"
  | "succeeded"
  | "failed"
  | "needs_human_review";

export type IssueSeverity = "error" | "warning";

export interface ValidationIssue {
  code: string;
  message: string;
  severity: IssueSeverity;
  field_path?: string | null;
}

export interface WorkflowFailure {
  step: string;
  disposition: string;
  message: string;
  error_type?: string | null;
  retry_count: number;
  issues: ValidationIssue[];
}

export interface HealthResponse {
  status: string;
  service: string;
}

export interface SubmitCaseRequest {
  case_path: string;
  workflow_id?: string | null;
  data_dir?: string;
  use_mock_crews?: boolean;
  model?: string | null;
  top_k?: number;
}

export interface CaseSummaryResponse {
  workflow_id: string;
  case_id?: string | null;
  status: WorkflowRunStatus;
  current_step?: string | null;
  issue_count: number;
  failure_count: number;
  issues: ValidationIssue[];
  failures: WorkflowFailure[];
}

export interface ExtractedFacts {
  case_id: string;
  requested_modality: string;
  requested_body_region: string;
  requested_laterality: string;
  symptom_duration_weeks?: number | null;
  symptom_duration_status: string;
  conservative_therapy_completed: string;
  prior_imaging_completed: string;
  red_flags_present: string;
  contraindications_present: string;
  diagnosis?: string | null;
  reason_for_order?: string | null;
  supporting_facts: Array<Record<string, unknown>>;
  missing_facts: string[];
}

export interface PolicyEvidence {
  evidence_id: string;
  document_id: string;
  chunk_id: string;
  citation_text: string;
  section_label?: string | null;
  relevance_score?: number | null;
  page_number?: number | null;
}

export interface RetrievalResult {
  query: {
    query_text: string;
    payer_id?: string | null;
    requested_modality?: string | null;
    requested_body_region?: string | null;
    study_family?: string | null;
    top_k: number;
    filters: Record<string, unknown>;
  };
  hits: Array<Record<string, unknown>>;
  evidence: PolicyEvidence[];
}

export interface PolicyMatchResult {
  case_id: string;
  payer_id: string;
  payer_name: string;
  requested_modality: string;
  requested_body_region: string;
  requested_laterality: string;
  recommendation_signal?: string;
  policy_requirements_summary: string;
  criteria: Array<Record<string, unknown>>;
  unresolved_questions: string[];
  cited_evidence: PolicyEvidence[];
}

export interface PriorAuthDraft {
  case_id: string;
  review_status: string;
  reviewer_summary: string;
  form_fields: Array<Record<string, unknown>>;
  missing_requirements: string[];
  unresolved_issues: string[];
  risk_flags: string[];
  submission_notes?: string | null;
}

export interface WorkflowResult {
  workflow_id: string;
  status: WorkflowRunStatus;
  artifacts: Record<string, unknown>;
  issues: ValidationIssue[];
  failures: WorkflowFailure[];
  step_history: Array<Record<string, unknown>>;
}

export interface SubmitCaseResponse {
  workflow: CaseSummaryResponse;
  result: WorkflowResult;
}

export interface ExtractedFactsResponse {
  workflow_id: string;
  status: WorkflowRunStatus;
  extracted_facts?: ExtractedFacts | null;
}

export interface PolicyEvidenceResponse {
  workflow_id: string;
  status: WorkflowRunStatus;
  retrieval_result?: RetrievalResult | null;
}

export interface PolicyMatchResponse {
  workflow_id: string;
  status: WorkflowRunStatus;
  policy_match_result?: PolicyMatchResult | null;
}

export interface DraftOutputResponse {
  workflow_id: string;
  status: WorkflowRunStatus;
  prior_auth_draft?: PriorAuthDraft | null;
}

export interface ChatContentBlock {
  type: string;
  text?: string | null;
  image_url?: string | null;
  metadata?: Record<string, unknown>;
}

export interface ChatMessage {
  role: string;
  content: ChatContentBlock[];
  name?: string | null;
  tool_call_id?: string | null;
  metadata?: Record<string, unknown>;
}

export interface ChatUsage {
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
}

export interface ChatToolCall {
  call_id: string;
  tool_name: string;
  arguments: Record<string, unknown>;
}

export interface ChatResponsePayload {
  model: {
    provider: string;
    family: string;
    model_id: string;
    display_name: string;
    base_url: string;
    transport: string;
    capabilities: Record<string, unknown>;
    metadata: Record<string, unknown>;
  };
  message: ChatMessage;
  finish_reason: string;
  usage: ChatUsage;
  tool_calls: ChatToolCall[];
  provider_response_id?: string | null;
  metadata?: Record<string, unknown>;
}

export interface CaseChatRequest {
  message: string;
}

export interface CaseChatResponse {
  workflow_id: string;
  status: WorkflowRunStatus;
  chat_response: ChatResponsePayload;
}

export interface ErrorEnvelope {
  error?: {
    code?: string;
    detail?: string;
  };
}
