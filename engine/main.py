"""Onus engine — FastAPI application entrypoint.

Schema is managed by Alembic migrations (run via `alembic upgrade head` on
container startup — see docker-compose.yml), not create_all.
"""
from fastapi import FastAPI

from routers import audit as audit_router
from routers import auth as auth_router
from routers import clients as clients_router
from routers import dashboard as dashboard_router
from routers import evaluations as evaluations_router
from routers import firms as firms_router
from routers import governance as governance_router
from routers import onboarding as onboarding_router
from routers import program as program_router
from routers import reports as reports_router
from routers import risk_assessment as risk_assessment_router

app = FastAPI(title="Onus Engine", version="0.1.0")

app.include_router(auth_router.router, prefix="/auth", tags=["auth"])
app.include_router(firms_router.router, prefix="/firms", tags=["firms"])
app.include_router(governance_router.router, prefix="/governance", tags=["governance"])
app.include_router(
    risk_assessment_router.router, prefix="/risk-assessment", tags=["risk-assessment"]
)
app.include_router(onboarding_router.router, prefix="/onboarding", tags=["onboarding"])
app.include_router(program_router.router, prefix="/program", tags=["program"])
app.include_router(clients_router.router, prefix="/clients", tags=["clients"])
app.include_router(clients_router.matters_router, prefix="/matters", tags=["matters"])
app.include_router(reports_router.router, prefix="/reports", tags=["reports"])
app.include_router(reports_router.records_router, prefix="/records", tags=["records"])
app.include_router(evaluations_router.router, prefix="/evaluations", tags=["evaluations"])
app.include_router(dashboard_router.router, prefix="/dashboard", tags=["dashboard"])
app.include_router(audit_router.router, prefix="/audit-log", tags=["audit"])


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "onus-engine"}
