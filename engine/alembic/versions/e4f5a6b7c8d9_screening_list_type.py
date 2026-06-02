"""generalise screening lists with a list_type (sanctions | pep)

Adds list_type to the screening tables so the same ingestion, versioning and matching
infrastructure serves both sanctions and PEP lists. Existing rows default to
'sanctions', so behaviour is unchanged.

Revision ID: e4f5a6b7c8d9
Revises: d3e4f5a6b7c8
Create Date: 2026-06-02 02:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e4f5a6b7c8d9'
down_revision: Union[str, Sequence[str], None] = 'd3e4f5a6b7c8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'sanctions_list_versions',
        sa.Column('list_type', sa.String(), server_default='sanctions', nullable=False),
    )
    op.add_column(
        'sanctions_screenings',
        sa.Column('list_type', sa.String(), server_default='sanctions', nullable=False),
    )


def downgrade() -> None:
    op.drop_column('sanctions_screenings', 'list_type')
    op.drop_column('sanctions_list_versions', 'list_type')
