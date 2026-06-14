from __future__ import annotations

from fastapi import FastAPI

from .routes import health_router


def create_app() -> FastAPI:
    app = FastAPI(title="AI Health Agent API", version="0.1.0")
    app.include_router(health_router)
    return app


app = create_app()
