from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from .dependencies import build_api_services
from .errors import register_error_handlers
from .routes import artifacts_router, cases_router, chat_router, health_router
from .store import InMemoryWorkflowStore

LOCAL_UI_ORIGINS = [
    "http://127.0.0.1:5173",
    "http://localhost:5173",
    "http://127.0.0.1:4173",
    "http://localhost:4173",
]


def create_app() -> FastAPI:
    load_dotenv()
    app = FastAPI(title="AI Health Agent API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=LOCAL_UI_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.workflow_store = InMemoryWorkflowStore()
    app.state.api_services = build_api_services(workflow_store=app.state.workflow_store)
    register_error_handlers(app)
    app.include_router(health_router)
    app.include_router(cases_router)
    app.include_router(artifacts_router)
    app.include_router(chat_router)
    return app


app = create_app()
