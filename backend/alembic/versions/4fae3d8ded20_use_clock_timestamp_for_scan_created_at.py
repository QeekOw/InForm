"""use clock_timestamp for scan created_at

Revision ID: 4fae3d8ded20
Revises: e627578b4362
Create Date: 2026-09-19 01:06:43.037998

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4fae3d8ded20'
down_revision: Union[str, None] = 'e627578b4362'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # now()/func.now() is frozen at the enclosing transaction's start time for
    # its whole duration, so two Scans saved in one transaction would get an
    # identical created_at — breaking "newest first" (issue #42) and the
    # staleness boundary (issue #43). clock_timestamp() advances on every call.
    op.execute("ALTER TABLE scans ALTER COLUMN created_at SET DEFAULT clock_timestamp()")


def downgrade() -> None:
    op.execute("ALTER TABLE scans ALTER COLUMN created_at SET DEFAULT now()")
