"""Add comment visibility

Revision ID: 20260213_000014
Revises: 20260213_000013
Create Date: 2026-02-13

"""
from alembic import op
import sqlalchemy as sa


revision = "20260213_000014"
down_revision = "20260213_000013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "comments",
        sa.Column(
            "is_public",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
            comment="True=공개, False=비공개",
        ),
    )


def downgrade() -> None:
    op.drop_column("comments", "is_public")
