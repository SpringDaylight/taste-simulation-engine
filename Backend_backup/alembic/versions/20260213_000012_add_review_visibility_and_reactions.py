"""Add review visibility and reaction counters

Revision ID: 20260213_000012
Revises: 20260213_000011
Create Date: 2026-02-13

"""
from alembic import op
import sqlalchemy as sa


revision = "20260213_000012"
down_revision = "20260213_000011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "reviews",
        sa.Column(
            "is_public",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
            comment="True=공개, False=비공개",
        ),
    )
    op.add_column(
        "reviews",
        sa.Column(
            "likes_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="좋아요 총합 캐시",
        ),
    )
    op.add_column(
        "reviews",
        sa.Column(
            "dislikes_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="싫어요 총합 캐시",
        ),
    )


def downgrade() -> None:
    op.drop_column("reviews", "dislikes_count")
    op.drop_column("reviews", "likes_count")
    op.drop_column("reviews", "is_public")
