from __future__ import annotations

from fastapi import Request

from .store import InMemoryWorkflowStore


def get_workflow_store(request: Request) -> InMemoryWorkflowStore:
    return request.app.state.workflow_store
