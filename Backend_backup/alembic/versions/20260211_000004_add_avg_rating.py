"""Add avg_rating to movies and backfill from reviews."""
from alembic import op
import sqlalchemy as sa


revision = "20260211_000004"
down_revision = "20260210_000003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("movies", sa.Column("avg_rating", sa.Numeric(2, 1), nullable=True))

    op.execute(
        """
        UPDATE movies
        SET avg_rating = sub.avg_rating
        FROM (
            SELECT movie_id, (ROUND(AVG(rating) * 2) / 2) AS avg_rating
            FROM reviews
            GROUP BY movie_id
        ) AS sub
        WHERE movies.id = sub.movie_id;
        """
    )


def downgrade() -> None:
    op.drop_column("movies", "avg_rating")
