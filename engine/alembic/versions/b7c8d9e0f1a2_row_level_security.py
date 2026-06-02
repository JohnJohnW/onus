"""row level security on firm-scoped tables

Enforces tenant isolation at the database. Every firm-owned table gets RLS with a
policy keyed on the app.current_firm_id GUC (set per request by the auth dependency
and the after_begin listener). FORCE is required because the app connects as the
table owner, which would otherwise bypass RLS. The policy fails closed: with no GUC
set, current_setting(..., true) is NULL and no rows match.

`users` and `firms` are intentionally excluded - login looks up a user by email
with no firm context yet, and signup creates the firm row itself. Those tables are
scoped in application code instead. `sanctions_list_versions`/`sanctions_entries`
are global reference data (no firm_id).

Revision ID: b7c8d9e0f1a2
Revises: f1a2b3c4d5e6
Create Date: 2026-06-02 00:30:00.000000
"""
from typing import Sequence, Union

from alembic import op


revision: str = 'b7c8d9e0f1a2'
down_revision: Union[str, Sequence[str], None] = 'f1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Firm-scoped tables (every table with a firm_id column, except users which must be
# queryable pre-authentication). Keep this list in step with new firm-owned tables.
TENANT_TABLES = [
    "agent_tasks",
    "aml_programs",
    "audit_log",
    "austrac_communications",
    "cdd_checks",
    "client_parties",
    "clients",
    "compliance_deadlines",
    "evaluation_findings",
    "evaluators",
    "firm_risk_states",
    "governance_approvals",
    "governance_roles",
    "independent_evaluations",
    "matters",
    "monitoring_alerts",
    "policies",
    "program_change_logs",
    "records",
    "report_decision_logs",
    "reports",
    "review_triggers",
    "risk_assessment_countries",
    "risk_assessment_customer_types",
    "risk_assessment_delivery_channels",
    "risk_assessment_services",
    "risk_assessments",
    "sanctions_screenings",
]

_POLICY = "firm_isolation"
# NULLIF(..., '') is essential: a custom GUC reverts to '' (not unset) after a
# SET LOCAL rolls back on a pooled connection, and ''::uuid would raise. NULLIF
# turns both unset and empty into NULL, so the policy fails closed (no rows) safely.
_PREDICATE = "firm_id = NULLIF(current_setting('app.current_firm_id', true), '')::uuid"


def upgrade() -> None:
    # RLS never applies to a superuser or to a role with BYPASSRLS, so the app must
    # connect as a least-privilege, non-superuser role. Create it and grant DML on the
    # current and (via default privileges) future tables. Migrations keep running as
    # the owner via ALEMBIC_DATABASE_URL. The dev password matches the rest of the
    # local stack; manage it via a secret in any real deployment.
    op.execute(
        """
        DO $$ BEGIN
          IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'onus_app') THEN
            CREATE ROLE onus_app LOGIN PASSWORD 'onus_local'
              NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;
          END IF;
        END $$;
        """
    )
    op.execute("GRANT USAGE ON SCHEMA public TO onus_app")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO onus_app")
    op.execute("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO onus_app")
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
        "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO onus_app"
    )
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO onus_app"
    )

    for table in TENANT_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY {_POLICY} ON {table} "
            f"USING ({_PREDICATE}) WITH CHECK ({_PREDICATE})"
        )


def downgrade() -> None:
    for table in TENANT_TABLES:
        op.execute(f"DROP POLICY IF EXISTS {_POLICY} ON {table}")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
