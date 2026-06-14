from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .store import WorkflowResultNotFoundError


class WorkflowExecutionError(RuntimeError):
    pass


def build_error_response(
    *,
    detail: str,
    error_code: str,
    status_code: int,
    extra: dict[str, Any] | None = None,
) -> JSONResponse:
    payload: dict[str, Any] = {
        "error": {
            "code": error_code,
            "detail": detail,
        }
    }
    if extra:
        payload["error"].update(extra)
    return JSONResponse(status_code=status_code, content=payload)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(WorkflowResultNotFoundError)
    async def workflow_not_found_handler(
        request: Request,
        exc: WorkflowResultNotFoundError,
    ) -> JSONResponse:
        del request
        return build_error_response(
            detail=str(exc),
            error_code="workflow_not_found",
            status_code=404,
        )

    @app.exception_handler(WorkflowExecutionError)
    async def workflow_execution_handler(
        request: Request,
        exc: WorkflowExecutionError,
    ) -> JSONResponse:
        del request
        return build_error_response(
            detail=str(exc),
            error_code="workflow_execution_failed",
            status_code=500,
        )
