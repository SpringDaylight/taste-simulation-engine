"""Add roulette rewards table and last_roulette_date

Revision ID: 20260213_000015
Revises: 20260213_000014
Create Date: 2026-02-13

"""
from alembic import op
import sqlalchemy as sa


revision = "20260213_000015"
down_revision = "20260213_000014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("last_roulette_date", sa.String(), nullable=True))

    op.create_table(
        "roulette_rewards",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("item", sa.String(), nullable=False),
        sa.Column("popcorn_gain", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("exp_gain", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rewarded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_foreign_key(
        "fk_roulette_rewards_user_id",
        "roulette_rewards",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_roulette_rewards_user_id", "roulette_rewards", ["user_id"])
    op.create_index("ix_roulette_rewards_user_rewarded", "roulette_rewards", ["user_id", "rewarded_at"])


def downgrade() -> None:
    op.drop_table("roulette_rewards")
    op.drop_column("users", "last_roulette_date")
