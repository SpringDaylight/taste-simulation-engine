"""Add user_auth table for social login."""
from alembic import op
import sqlalchemy as sa


revision = "20260211_000006"
down_revision = "20260211_000005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_auth",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("provider_user_id", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("connected_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("provider", "provider_user_id", name="uq_user_auth_provider_user"),
    )
    op.create_index("ix_user_auth_user_id", "user_auth", ["user_id"])
    op.create_index("ix_user_auth_provider_user", "user_auth", ["provider", "provider_user_id"])


def downgrade() -> None:
    op.drop_index("ix_user_auth_provider_user", table_name="user_auth")
    op.drop_index("ix_user_auth_user_id", table_name="user_auth")
    op.drop_table("user_auth")
