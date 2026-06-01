"""Onus engine — FastAPI application entrypoint."""
from contextlib import asynccontextmanager

from fastapi import FastAPI

import models  # noqa: F401  (import so models register on Base.metadata)
from database import Base, engine
from routers import auth as auth_router
from routers import dashboard as dashboard_router
from routers import risk_assessment as risk_assessment_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Dev convenience: ensure tables exist on startup. In production, manage the
    # schema with Alembic migrations (engine/alembic) instead of create_all.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Onus Engine", version="0.1.0", lifespan=lifespan)

app.include_router(auth_router.router, prefix="/auth", tags=["auth"])
app.include_router(dashboard_router.router, prefix="/dashboard", tags=["dashboard"])
app.include_router(
    risk_assessment_router.router, prefix="/risk-assessment", tags=["risk-assessment"]
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "onus-engine"}
