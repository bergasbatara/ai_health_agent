import type { WorkflowRunStatus } from "../types/api";

export function toStatusTone(status: string | null | undefined): string {
  if (!status) {
    return "idle";
  }

  return status.trim().toLowerCase().replace(/[\s_]+/g, "-");
}

export function formatWorkflowStatus(status: WorkflowRunStatus): string {
  return status.replace(/_/g, " ");
}
