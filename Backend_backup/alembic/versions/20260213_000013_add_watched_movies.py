"""Add watched movies table

Revision ID: 20260213_000013
Revises: 20260213_000012
Create Date: 2026-02-13

"""
from alembic import op
import sqlalchemy as sa


revision = "20260213_000013"
down_revision = "20260213_000012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "watched_movies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("movie_id", sa.Integer(), nullable=False),
        sa.Column("watched_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_foreign_key(
        "fk_watched_movies_user_id",
        "watched_movies",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE"
    )
    op.create_foreign_key(
        "fk_watched_movies_movie_id",
        "watched_movies",
        "movies",
        ["movie_id"],
        ["id"],
        ondelete="CASCADE"
    )

    op.create_index("ix_watched_movies_user_id", "watched_movies", ["user_id"])
    op.create_index("ix_watched_movies_movie_id", "watched_movies", ["movie_id"])
    op.create_index("ix_watched_movies_user_movie", "watched_movies", ["user_id", "movie_id"])
    op.create_unique_constraint("uq_user_movie_watched", "watched_movies", ["user_id", "movie_id"])


def downgrade() -> None:
    op.drop_table("watched_movies")
