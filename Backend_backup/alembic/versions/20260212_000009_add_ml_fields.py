"""Add ML fields for preferences and movie vectors."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260212_000009"
down_revision = "20260212_000008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user_preferences",
        sa.Column(
            "dislike_tags",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "movie_vectors",
        sa.Column(
            "direction_mood",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column(
        "movie_vectors",
        sa.Column(
            "character_relationship",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column(
        "movie_vectors",
        sa.Column("embedding_text", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("movie_vectors", "embedding_text")
    op.drop_column("movie_vectors", "character_relationship")
    op.drop_column("movie_vectors", "direction_mood")
    op.drop_column("user_preferences", "dislike_tags")
