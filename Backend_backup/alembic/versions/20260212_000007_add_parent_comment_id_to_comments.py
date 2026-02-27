"""Add parent_comment_id to comments."""
from alembic import op
import sqlalchemy as sa


revision = "20260212_000007"
down_revision = "20260211_000006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "comments",
        sa.Column("parent_comment_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_comments_parent_comment_id",
        "comments",
        ["parent_comment_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_comments_parent_comment_id",
        "comments",
        "comments",
        ["parent_comment_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("fk_comments_parent_comment_id", "comments", type_="foreignkey")
    op.drop_index("ix_comments_parent_comment_id", table_name="comments")
    op.drop_column("comments", "parent_comment_id")
