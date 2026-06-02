"""data residency attestation (firm-scoped, with RLS)

A firm's record of where its data is hosted and the governance sign-off for that
choice (see the data-residency guidance in the README). One row per firm, upserted.

Revision ID: a7b8c9d0e1f2
Revises: e4f5a6b7c8d9
Create Date: 2026-06-03 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a7b8c9d0e1f2'
down_revision: Union[str, Sequence[str], None] = 'e4f5a6b7c8d9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_PREDICATE = "firm_id = NULLIF(current_setting('app.current_firm_id', true), '')::uuid"


def upgrade() -> None:
    op.create_table(
        'data_residency_attestations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('firm_id', sa.UUID(), nullable=False),
        sa.Column('data_region', sa.String(), nullable=False),
        sa.Column('hosting_provider', sa.String(), nullable=True),
        sa.Column('cross_border', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('dpa_in_place', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('approved_by_name', sa.String(), nullable=True),
        sa.Column('attested_on', sa.Date(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['firm_id'], ['firms.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('firm_id', name='uq_data_residency_attestations_firm'),
    )

    # Firm isolation, consistent with the other tenant tables (b7c8d9e0f1a2).
    op.execute("ALTER TABLE data_residency_attestations ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE data_residency_attestations FORCE ROW LEVEL SECURITY")
    op.execute(
        f"CREATE POLICY firm_isolation ON data_residency_attestations "
        f"USING ({_PREDICATE}) WITH CHECK ({_PREDICATE})"
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS firm_isolation ON data_residency_attestations")
    op.drop_table('data_residency_attestations')
