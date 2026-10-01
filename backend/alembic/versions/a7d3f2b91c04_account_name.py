"""account display name

Adds a nullable `name` column to `accounts`, used only for display (dashboard
greeting, profile page). `scans` is untouched.

Revision ID: a7d3f2b91c04
Revises: c5e21d8758b1
Create Date: 2026-10-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a7d3f2b91c04'
down_revision: Union[str, None] = 'c5e21d8758b1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('accounts', sa.Column('name', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('accounts', 'name')
