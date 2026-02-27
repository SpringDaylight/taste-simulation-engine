"""Add birth_date and gender to users."""
from alembic import op
import sqlalchemy as sa


revision = "20260212_000008"
down_revision = "20260212_000007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("birth_date", sa.Date(), nullable=True))
    op.add_column("users", sa.Column("gender", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "gender")
    op.drop_column("users", "birth_date")
