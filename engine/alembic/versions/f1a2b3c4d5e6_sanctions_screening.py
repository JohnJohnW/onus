"""sanctions screening

Revision ID: f1a2b3c4d5e6
Revises: 6a7e2ea6b4ea
Create Date: 2026-06-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, Sequence[str], None] = '6a7e2ea6b4ea'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'sanctions_list_versions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('source', sa.String(), nullable=False),
        sa.Column('origin', sa.String(), nullable=False),
        sa.Column('fetched_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('content_hash', sa.String(), nullable=False),
        sa.Column('entry_count', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('is_current', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('note', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_sanctions_list_versions_is_current'), 'sanctions_list_versions', ['is_current'], unique=False
    )

    op.create_table(
        'sanctions_entries',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('version_id', sa.UUID(), nullable=False),
        sa.Column('reference', sa.String(), nullable=True),
        sa.Column('entity_type', sa.String(), server_default='unknown', nullable=False),
        sa.Column('primary_name', sa.String(), nullable=False),
        sa.Column('search_names', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('aliases', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('dob', sa.String(), nullable=True),
        sa.Column('place_of_birth', sa.String(), nullable=True),
        sa.Column('citizenship', sa.String(), nullable=True),
        sa.Column('address', sa.String(), nullable=True),
        sa.Column('listing_info', sa.String(), nullable=True),
        sa.Column('raw', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['version_id'], ['sanctions_list_versions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_sanctions_entries_version_id'), 'sanctions_entries', ['version_id'], unique=False
    )

    op.create_table(
        'sanctions_screenings',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('firm_id', sa.UUID(), nullable=False),
        sa.Column('subject_type', sa.String(), nullable=True),
        sa.Column('subject_id', sa.UUID(), nullable=True),
        sa.Column('query_name', sa.String(), nullable=False),
        sa.Column('version_id', sa.UUID(), nullable=True),
        sa.Column('match_count', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('top_score', sa.Numeric(precision=4, scale=3), nullable=True),
        sa.Column('status', sa.String(), server_default='screened', nullable=False),
        sa.Column('decision_note', sa.Text(), nullable=True),
        sa.Column('matches', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('screened_by_user_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['firm_id'], ['firms.id'], ),
        sa.ForeignKeyConstraint(['version_id'], ['sanctions_list_versions.id'], ),
        sa.ForeignKeyConstraint(['screened_by_user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_sanctions_screenings_firm_id'), 'sanctions_screenings', ['firm_id'], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_sanctions_screenings_firm_id'), table_name='sanctions_screenings')
    op.drop_table('sanctions_screenings')
    op.drop_index(op.f('ix_sanctions_entries_version_id'), table_name='sanctions_entries')
    op.drop_table('sanctions_entries')
    op.drop_index(op.f('ix_sanctions_list_versions_is_current'), table_name='sanctions_list_versions')
    op.drop_table('sanctions_list_versions')
