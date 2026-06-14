from __future__ import annotations

from fastapi import FastAPI

from .dependencies import ApiServices
from .routes import artifacts_router, cases_router, health_router
from .store import InMemoryWorkflowStore


def create_app() -> FastAPI:
    app = FastAPI(title="AI Health Agent API", version="0.1.0")
    app.state.workflow_store = InMemoryWorkflowStore()
    app.state.api_services = ApiServices(workflow_store=app.state.workflow_store)
    app.include_router(health_router)
    app.include_router(cases_router)
    app.include_router(artifacts_router)
    return app


app = create_app()
