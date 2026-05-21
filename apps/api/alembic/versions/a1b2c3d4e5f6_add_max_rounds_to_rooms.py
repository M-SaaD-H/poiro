"""add_max_rounds_to_rooms

Revision ID: a1b2c3d4e5f6
Revises: 
Create Date: 2026-05-21 08:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'a1b2c3d4e5f6'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'rooms',
        sa.Column('max_rounds', sa.Integer(), nullable=False, server_default='3'),
    )


def downgrade() -> None:
    op.drop_column('rooms', 'max_rounds')
