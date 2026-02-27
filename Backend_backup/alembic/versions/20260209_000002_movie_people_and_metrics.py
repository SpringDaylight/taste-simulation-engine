from alembic import op
import sqlalchemy as sa


revision = "20260209_000002"
down_revision = "20260206_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("movies", sa.Column("original_title", sa.String(), nullable=True))
    op.add_column("movies", sa.Column("vote_average", sa.Float(), nullable=True))
    op.add_column("movies", sa.Column("vote_count", sa.Integer(), nullable=True))

    op.create_table(
        "movie_directors",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("movie_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
    )
    op.create_index("idx_movie_directors_movie_id", "movie_directors", ["movie_id"])

    op.create_table(
        "movie_cast",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("movie_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
    )
    op.create_index("idx_movie_cast_movie_id", "movie_cast", ["movie_id"])


def downgrade() -> None:
    op.drop_index("idx_movie_cast_movie_id", table_name="movie_cast")
    op.drop_table("movie_cast")

    op.drop_index("idx_movie_directors_movie_id", table_name="movie_directors")
    op.drop_table("movie_directors")

    op.drop_column("movies", "vote_count")
    op.drop_column("movies", "vote_average")
    op.drop_column("movies", "original_title")
