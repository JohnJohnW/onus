"""Onus engine - FastAPI application entrypoint.

Schema is managed by Alembic migrations (run via `alembic upgrade head` on
container startup - see docker-compose.yml), not create_all.
"""
import logging
import os

from fastapi import FastAPI, Request

from routers import alerts as alerts_router
from routers import attestation as attestation_router
from routers import audit as audit_router
from routers import auth as auth_router
from routers import clients as clients_router
from routers import dashboard as dashboard_router
from routers import documents as documents_router
from routers import eoi as eoi_router
from routers import evaluations as evaluations_router
from routers import firms as firms_router
from routers import governance as governance_router
from routers import onboarding as onboarding_router
from routers import program as program_router
from routers import reports as reports_router
from routers import risk_assessment as risk_assessment_router
from routers import sanctions as sanctions_router

logger = logging.getLogger("onus")


def _check_config() -> None:
    """Fail fast (in production) or warn (in dev) on an obviously weak signing secret.

    The dev default in .env.local is a long random value; production must inject its
    own via a secrets manager. ONUS_ENV=production turns the warning into a hard stop.
    """
    secret = os.environ.get("JWT_SECRET", "")
    env = os.environ.get("ONUS_ENV", "development").lower()
    weak = len(secret) < 32 or secret.lower() in {"", "changeme", "secret", "dev", "devsecret", "please-change-me"}
    if weak:
        msg = "JWT_SECRET is missing or weak - set a long random value via your secrets manager."
        if env == "production":
            raise RuntimeError(f"Refusing to start in production: {msg}")
        logger.warning("Onus config check: %s", msg)


_check_config()

app = FastAPI(title="Onus Engine", version="0.1.0")


# Defence-in-depth security headers on every response. The engine normally sits behind
# the web proxy, but these are cheap and protect any direct access. TLS/HSTS is the
# responsibility of the reverse proxy / load balancer that terminates HTTPS in production.
_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Cache-Control": "no-store",
}


@app.middleware("http")
async def _security_headers(request: Request, call_next):
    response = await call_next(request)
    for key, value in _SECURITY_HEADERS.items():
        response.headers.setdefault(key, value)
    return response


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
app.include_router(alerts_router.router, prefix="/alerts", tags=["alerts"])
app.include_router(reports_router.router, prefix="/reports", tags=["reports"])
app.include_router(reports_router.records_router, prefix="/records", tags=["records"])
app.include_router(evaluations_router.router, prefix="/evaluations", tags=["evaluations"])
app.include_router(dashboard_router.router, prefix="/dashboard", tags=["dashboard"])
app.include_router(audit_router.router, prefix="/audit-log", tags=["audit"])
app.include_router(sanctions_router.router, prefix="/sanctions", tags=["sanctions"])
app.include_router(documents_router.router, prefix="/documents", tags=["documents"])
app.include_router(attestation_router.router, prefix="/attestation", tags=["attestation"])
app.include_router(eoi_router.router, prefix="/eoi", tags=["eoi"])


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "onus-engine"}


@app.get("/debug/db")
def debug_db() -> dict:
    """TEMPORARY deploy diagnostic - reports the DB connection target (password masked)
    and whether a trivial query succeeds. Removed after the demo deploy is verified."""
    from sqlalchemy import text as _text

    from database import engine as _engine

    u = _engine.url
    conn_info = {"user": u.username, "host": u.host, "port": u.port, "database": u.database}
    try:
        with _engine.connect() as connection:
            connection.execute(_text("select 1"))
        return {"db": "ok", "conn": conn_info}
    except Exception as exc:  # noqa: BLE001 - surface the cause for diagnosis
        return {"db": "error", "type": type(exc).__name__, "detail": str(exc)[:400], "conn": conn_info}
