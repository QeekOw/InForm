"""account profile defaults and google_sub

Adds pre-fill-only profile defaults to `accounts`, plus the `google_sub` column
that real Google sign-in will match on later, and makes `password_hash` nullable
so a Google-only account is representable.

`scans` is deliberately untouched. A Scan's frozen `profile` snapshot stays the
only source of truth for what produced a given plan, which is what keeps issue
#42's immutability guarantee intact — the new `accounts` columns are form
pre-fill and nothing else.

Revision ID: c5e21d8758b1
Revises: 4fae3d8ded20
Create Date: 2026-09-20 00:27:50.520296

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c5e21d8758b1'
down_revision: Union[str, None] = '4fae3d8ded20'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Named so the constraint can be dropped by name on downgrade; Alembic does not
# autogenerate CHECK constraints, so this pair is written by hand.
_CREDENTIAL_CHECK = "ck_accounts_has_a_credential"


def upgrade() -> None:
    op.add_column('accounts', sa.Column('google_sub', sa.String(), nullable=True))
    op.add_column('accounts', sa.Column('date_of_birth', sa.Date(), nullable=True))
    op.add_column('accounts', sa.Column('height_cm', sa.Float(), nullable=True))
    op.add_column('accounts', sa.Column('default_biological_sex', sa.String(), nullable=True))
    op.add_column('accounts', sa.Column('default_activity_multiplier', sa.Float(), nullable=True))
    op.add_column('accounts', sa.Column('default_fitness_goal', sa.String(), nullable=True))
    op.alter_column('accounts', 'password_hash',
               existing_type=sa.VARCHAR(),
               nullable=True)
    op.create_index(op.f('ix_accounts_google_sub'), 'accounts', ['google_sub'], unique=True)

    # Dropping NOT NULL from password_hash would otherwise allow a row with no
    # password and no Google identity: an account nobody could ever sign into.
    # Added after the column is nullable so the two changes can't be applied in
    # an order that briefly permits one.
    op.create_check_constraint(
        _CREDENTIAL_CHECK,
        'accounts',
        'password_hash IS NOT NULL OR google_sub IS NOT NULL',
    )


def downgrade() -> None:
    op.drop_constraint(_CREDENTIAL_CHECK, 'accounts', type_='check')
    op.drop_index(op.f('ix_accounts_google_sub'), table_name='accounts')
    # Rows with a google_sub but no password_hash would block this; there are
    # none until Google sign-in is implemented, and by then this downgrade is
    # no longer meaningful anyway.
    op.alter_column('accounts', 'password_hash',
               existing_type=sa.VARCHAR(),
               nullable=False)
    op.drop_column('accounts', 'default_fitness_goal')
    op.drop_column('accounts', 'default_activity_multiplier')
    op.drop_column('accounts', 'default_biological_sex')
    op.drop_column('accounts', 'height_cm')
    op.drop_column('accounts', 'date_of_birth')
    op.drop_column('accounts', 'google_sub')
