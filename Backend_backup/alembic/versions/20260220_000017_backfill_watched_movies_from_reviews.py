"""Backfill watched_movies from existing reviews

Revision ID: 20260220_000017
Revises: 20260220_000016
Create Date: 2026-02-20

"""
from alembic import op


revision = "20260220_000017"
down_revision = "20260220_000016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO watched_movies (user_id, movie_id, watched_at)
        SELECT DISTINCT r.user_id, r.movie_id, NOW()
        FROM reviews r
        ON CONFLICT (user_id, movie_id) DO NOTHING
        """
    )


def downgrade() -> None:
    # Data backfill migration has no safe rollback.
    pass
