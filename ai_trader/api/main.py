"""FastAPI application entrypoint stub."""

from fastapi import FastAPI

from api.routes.dossier import router as dossier_router
from api.routes.health import router as health_router
from api.routes.run import router as run_router

app = FastAPI(title="AI Trader")

app.include_router(health_router, prefix="/api")
app.include_router(dossier_router, prefix="/api")
app.include_router(run_router, prefix="/api")

__all__ = ["app"]
