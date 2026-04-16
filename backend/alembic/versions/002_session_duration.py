"""Session active duration columns

Revision ID: 002
Revises: 001
Create Date: 2026-04-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "sessions",
        sa.Column("total_paused_seconds", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "sessions",
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
    )
    # Completed rows without pause history: backfill wall-clock duration in app/API if null.


def downgrade() -> None:
    op.drop_column("sessions", "duration_seconds")
    op.drop_column("sessions", "total_paused_seconds")
