"""data-model hardening: governance unique constraint + cascade on component FKs

- One governance role per (firm, role): a DB unique constraint behind the app's
  check-then-act assignment, so a race cannot create two compliance officers.
- ON DELETE CASCADE on the FKs of the ephemeral component children that the ORM
  already marks delete-orphan (risk-assessment sub-tables, policies, evaluation
  components), so the database and ORM agree. The retention-bound subtree
  (clients / matters / reports / records) is deliberately left RESTRICT - cascading
  a delete there would violate the 7-year retention obligation.

Revision ID: d3e4f5a6b7c8
Revises: c2d3e4f5a6b7
Create Date: 2026-06-02 01:30:00.000000
"""
from typing import Sequence, Union

from alembic import op


revision: str = 'd3e4f5a6b7c8'
down_revision: Union[str, Sequence[str], None] = 'c2d3e4f5a6b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# (table, fk_constraint_name, referent_table, local_column)
_CASCADE_FKS = [
    ("risk_assessment_services", "risk_assessment_services_risk_assessment_id_fkey", "risk_assessments", "risk_assessment_id"),
    ("risk_assessment_customer_types", "risk_assessment_customer_types_risk_assessment_id_fkey", "risk_assessments", "risk_assessment_id"),
    ("risk_assessment_delivery_channels", "risk_assessment_delivery_channels_risk_assessment_id_fkey", "risk_assessments", "risk_assessment_id"),
    ("risk_assessment_countries", "risk_assessment_countries_risk_assessment_id_fkey", "risk_assessments", "risk_assessment_id"),
    ("policies", "policies_program_id_fkey", "aml_programs", "program_id"),
    ("evaluators", "evaluators_evaluation_id_fkey", "independent_evaluations", "evaluation_id"),
    ("evaluation_reports", "evaluation_reports_evaluation_id_fkey", "independent_evaluations", "evaluation_id"),
    ("evaluation_findings", "evaluation_findings_evaluation_id_fkey", "independent_evaluations", "evaluation_id"),
]


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_governance_roles_firm_role", "governance_roles", ["firm_id", "role"]
    )
    for table, fk, referent, column in _CASCADE_FKS:
        op.drop_constraint(fk, table, type_="foreignkey")
        op.create_foreign_key(fk, table, referent, [column], ["id"], ondelete="CASCADE")


def downgrade() -> None:
    for table, fk, referent, column in _CASCADE_FKS:
        op.drop_constraint(fk, table, type_="foreignkey")
        op.create_foreign_key(fk, table, referent, [column], ["id"])
    op.drop_constraint("uq_governance_roles_firm_role", "governance_roles", type_="unique")
