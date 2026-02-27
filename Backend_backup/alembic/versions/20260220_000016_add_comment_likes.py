"""Add comment likes and reaction counters

Revision ID: 20260220_000016
Revises: 20260213_000015
Create Date: 2026-02-20

"""
from alembic import op
import sqlalchemy as sa


revision = "20260220_000016"
down_revision = "20260213_000015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "comments",
        sa.Column(
            "likes_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="좋아요 총합 캐시",
        ),
    )
    op.add_column(
        "comments",
        sa.Column(
            "dislikes_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="싫어요 총합 캐시",
        ),
    )

    op.create_table(
        "comment_likes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("comment_id", sa.Integer(), sa.ForeignKey("comments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("is_like", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("comment_id", "user_id", name="uq_comment_user_like"),
    )
    op.create_index("ix_comment_likes_comment_id", "comment_likes", ["comment_id"])
    op.create_index("ix_comment_likes_user_id", "comment_likes", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_comment_likes_user_id", table_name="comment_likes")
    op.drop_index("ix_comment_likes_comment_id", table_name="comment_likes")
    op.drop_table("comment_likes")
    op.drop_column("comments", "dislikes_count")
    op.drop_column("comments", "likes_count")
