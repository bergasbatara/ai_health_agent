from __future__ import annotations

from collections.abc import Iterable

from domain import ExtractedClinicalFacts, PolicyMatchResult, PriorAuthDraft
from orchestration import WorkflowResult
from retrieval import RetrievalResult


class WorkflowResultNotFoundError(KeyError):
    pass


class InMemoryWorkflowStore:
    def __init__(self) -> None:
        self._results_by_workflow_id: dict[str, WorkflowResult] = {}
        self._workflow_id_by_case_id: dict[str, str] = {}

    def save_result(self, result: WorkflowResult) -> WorkflowResult:
        self._results_by_workflow_id[result.workflow_id] = result
        patient_case = result.artifacts.patient_case
        if patient_case is not None:
            self._workflow_id_by_case_id[patient_case.case_id] = result.workflow_id
        return result

    def get_result(self, workflow_id: str) -> WorkflowResult:
        try:
            return self._results_by_workflow_id[workflow_id]
        except KeyError as exc:
            raise WorkflowResultNotFoundError(f"Workflow result not found: {workflow_id}") from exc

    def get_result_by_case_id(self, case_id: str) -> WorkflowResult:
        try:
            workflow_id = self._workflow_id_by_case_id[case_id]
        except KeyError as exc:
            raise WorkflowResultNotFoundError(f"No workflow result found for case id: {case_id}") from exc
        return self.get_result(workflow_id)

    def has_workflow(self, workflow_id: str) -> bool:
        return workflow_id in self._results_by_workflow_id

    def list_results(self) -> list[WorkflowResult]:
        return list(self._results_by_workflow_id.values())

    def list_workflow_ids(self) -> list[str]:
        return list(self._results_by_workflow_id.keys())

    def get_extracted_facts(self, workflow_id: str) -> ExtractedClinicalFacts | None:
        return self.get_result(workflow_id).artifacts.extracted_facts

    def get_retrieval_result(self, workflow_id: str) -> RetrievalResult | None:
        return self.get_result(workflow_id).artifacts.retrieval_result

    def get_policy_match_result(self, workflow_id: str) -> PolicyMatchResult | None:
        return self.get_result(workflow_id).artifacts.policy_match_result

    def get_prior_auth_draft(self, workflow_id: str) -> PriorAuthDraft | None:
        return self.get_result(workflow_id).artifacts.prior_auth_draft

    def delete_result(self, workflow_id: str) -> WorkflowResult:
        result = self.get_result(workflow_id)
        del self._results_by_workflow_id[workflow_id]
        patient_case = result.artifacts.patient_case
        if patient_case is not None and self._workflow_id_by_case_id.get(patient_case.case_id) == workflow_id:
            del self._workflow_id_by_case_id[patient_case.case_id]
        return result

    def save_all(self, results: Iterable[WorkflowResult]) -> list[WorkflowResult]:
        saved: list[WorkflowResult] = []
        for result in results:
            saved.append(self.save_result(result))
        return saved
