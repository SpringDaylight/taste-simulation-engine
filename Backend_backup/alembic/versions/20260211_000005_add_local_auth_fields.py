"""Add local auth fields to users."""
from alembic import op
import sqlalchemy as sa


revision = "20260211_000005"
down_revision = "20260211_000004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("user_id", sa.String(), nullable=True))
    op.add_column("users", sa.Column("nickname", sa.String(), nullable=True))
    op.add_column("users", sa.Column("email", sa.String(), nullable=True))
    op.add_column("users", sa.Column("password_hash", sa.String(), nullable=True))

    op.create_index("ix_users_user_id", "users", ["user_id"], unique=True)
    op.create_index("ix_users_nickname", "users", ["nickname"], unique=True)
    op.create_index("ix_users_email", "users", ["email"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_nickname", table_name="users")
    op.drop_index("ix_users_user_id", table_name="users")

    op.drop_column("users", "password_hash")
    op.drop_column("users", "email")
    op.drop_column("users", "nickname")
    op.drop_column("users", "user_id")
