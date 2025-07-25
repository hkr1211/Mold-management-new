"""Add system_logs table

Revision ID: b24a4b6fdb9a
Revises: 196c0ffaa7df
Create Date: 2025-06-24 10:29:57.708471

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b24a4b6fdb9a'
down_revision: Union[str, Sequence[str], None] = '196c0ffaa7df'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('system_logs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id_fk', sa.Integer(), nullable=True),
    sa.Column('action_type', sa.String(length=100), nullable=False),
    sa.Column('target_resource', sa.String(length=100), nullable=True),
    sa.Column('target_id', sa.String(length=100), nullable=True),
    sa.Column('details', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['user_id_fk'], ['users.id'], name=op.f('fk_system_logs_user_id_fk_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_system_logs'))
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('system_logs')
    # ### end Alembic commands ###
