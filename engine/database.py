"""SQLAlchemy engine, session factory, and declarative Base for the Onus engine."""
from __future__ import annotations

import os

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, declarative_base, sessionmaker
from sqlalchemy.pool import NullPool

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://onus:onus_local@localhost:5432/onus"
)

# On Vercel's serverless runtime the function is short-lived and sits behind Supabase's
# transaction pooler (pgbouncer), which does the real connection pooling. Holding a
# SQLAlchemy pool there is wrong, and pool_pre_ping just adds a round-trip per request,
# so use NullPool: each request checks out a fresh, cheap pooled connection and returns
# it. A long-running deployment (Docker / a persistent host) keeps a normal pool with
# pre-ping. (VERCEL is set automatically on Vercel.)
if os.environ.get("VERCEL"):
    engine = create_engine(
        DATABASE_URL, poolclass=NullPool, future=True, connect_args={"connect_timeout": 10}
    )
else:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()


@event.listens_for(Session, "after_begin")
def _apply_firm_rls_guc(session: Session, transaction, connection) -> None:
    """Pin app.current_firm_id at the start of every transaction, from session.info.

    Postgres row-level security policies scope every firm-owned table to this GUC.
    We set it transaction-local (is_local=true), so it is cleared automatically at
    commit/rollback - a pooled connection therefore never carries one firm's context
    into another request. Because SQLAlchemy checks out a fresh connection per
    transaction, re-applying here (rather than once) is what keeps RLS correct across
    commits within a single request. When firm_id is absent (auth bootstrap), the GUC
    stays unset and the policies fail closed (no rows)."""
    firm_id = session.info.get("firm_id")
    if firm_id:
        connection.execute(
            text("SELECT set_config('app.current_firm_id', :fid, true)"),
            {"fid": str(firm_id)},
        )


def set_session_firm(db: Session, firm_id) -> None:
    """Bind a firm to this session for RLS: stamp session.info (so every later
    transaction re-applies the GUC via the listener) and set it on the current
    transaction immediately (the listener does not re-fire for an already-open one)."""
    db.info["firm_id"] = str(firm_id)
    db.execute(
        text("SELECT set_config('app.current_firm_id', :fid, true)"),
        {"fid": str(firm_id)},
    )


def get_db():
    """FastAPI dependency that yields a database session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
