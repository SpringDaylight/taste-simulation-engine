"""Rename reviews to tmdb_reviews and create new user reviews table

Revision ID: 20260213_000011
Revises: 20260212_000010
Create Date: 2026-02-13

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260213_000011"
down_revision = "20260212_000010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    
    # Get existing indexes and constraints
    existing_indexes = [idx['name'] for idx in inspector.get_indexes('reviews')]
    existing_constraints = [con['name'] for con in inspector.get_foreign_keys('reviews')]
    existing_constraints += [con['name'] for con in inspector.get_unique_constraints('reviews')]
    
    # 1. Drop existing foreign key constraints from reviews table
    if "fk_reviews_user_id" in existing_constraints:
        op.drop_constraint("fk_reviews_user_id", "reviews", type_="foreignkey")
    if "fk_reviews_movie_id" in existing_constraints:
        op.drop_constraint("fk_reviews_movie_id", "reviews", type_="foreignkey")
    
    # 2. Drop existing indexes and constraints from reviews table
    if "uq_user_movie_review" in existing_constraints:
        op.drop_constraint("uq_user_movie_review", "reviews", type_="unique")
    if "ix_reviews_user_movie" in existing_indexes:
        op.drop_index("ix_reviews_user_movie", table_name="reviews")
    if "ix_reviews_user_id" in existing_indexes:
        op.drop_index("ix_reviews_user_id", table_name="reviews")
    if "ix_reviews_movie_id" in existing_indexes:
        op.drop_index("ix_reviews_movie_id", table_name="reviews")
    
    # 3. Rename existing reviews table to tmdb_reviews
    op.rename_table("reviews", "tmdb_reviews")
    
    # 4. Rename indexes for tmdb_reviews
    op.execute("ALTER INDEX IF EXISTS idx_reviews_movie_created RENAME TO idx_tmdb_reviews_movie_created")
    op.execute("ALTER INDEX IF EXISTS idx_reviews_user_created RENAME TO idx_tmdb_reviews_user_created")
    
    # 5. Drop old tables if they exist
    existing_tables = inspector.get_table_names()
    
    if "comments" in existing_tables:
        op.drop_table("comments")
    if "review_likes" in existing_tables:
        op.drop_table("review_likes")
    
    # 4. Create new reviews table for user reviews
    op.create_table(
        "reviews",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("movie_id", sa.Integer(), nullable=False),
        sa.Column("rating", sa.Numeric(2, 1), nullable=False, comment="0.5~5.0, 0.5 단위"),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    
    # Add foreign keys
    op.create_foreign_key(
        "fk_reviews_user_id",
        "reviews",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE"
    )
    op.create_foreign_key(
        "fk_reviews_movie_id",
        "reviews",
        "movies",
        ["movie_id"],
        ["id"],
        ondelete="CASCADE"
    )
    
    # Add indexes and constraints
    op.create_index("ix_reviews_user_id", "reviews", ["user_id"])
    op.create_index("ix_reviews_movie_id", "reviews", ["movie_id"])
    op.create_index("ix_reviews_user_movie", "reviews", ["user_id", "movie_id"])
    op.create_unique_constraint("uq_user_movie_review", "reviews", ["user_id", "movie_id"])
    
    # 5. Create new review_likes table
    op.create_table(
        "review_likes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("review_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("is_like", sa.Boolean(), nullable=False, server_default="true", comment="True=좋아요, False=싫어요"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    
    op.create_foreign_key(
        "fk_review_likes_review_id",
        "review_likes",
        "reviews",
        ["review_id"],
        ["id"],
        ondelete="CASCADE"
    )
    op.create_foreign_key(
        "fk_review_likes_user_id",
        "review_likes",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE"
    )
    
    op.create_index("ix_review_likes_review_id", "review_likes", ["review_id"])
    op.create_index("ix_review_likes_user_id", "review_likes", ["user_id"])
    op.create_unique_constraint("uq_review_user_like", "review_likes", ["review_id", "user_id"])
    
    # 6. Create new comments table
    op.create_table(
        "comments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("review_id", sa.Integer(), nullable=False),
        sa.Column("parent_comment_id", sa.Integer(), nullable=True),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    
    op.create_foreign_key(
        "fk_comments_review_id",
        "comments",
        "reviews",
        ["review_id"],
        ["id"],
        ondelete="CASCADE"
    )
    op.create_foreign_key(
        "fk_comments_parent_comment_id",
        "comments",
        "comments",
        ["parent_comment_id"],
        ["id"],
        ondelete="CASCADE"
    )
    op.create_foreign_key(
        "fk_comments_user_id",
        "comments",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE"
    )
    
    op.create_index("ix_comments_review_id", "comments", ["review_id"])
    op.create_index("ix_comments_parent_comment_id", "comments", ["parent_comment_id"])
    op.create_index("ix_comments_user_id", "comments", ["user_id"])


def downgrade() -> None:
    # Drop new tables
    op.drop_table("comments")
    op.drop_table("review_likes")
    op.drop_table("reviews")
    
    # Recreate old review_likes and review_comments
    op.create_table(
        "review_likes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("review_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_unique_constraint("uq_review_likes", "review_likes", ["review_id", "user_id"])
    
    op.create_table(
        "review_comments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("review_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("idx_comments_review_created", "review_comments", ["review_id", "created_at"])
    
    # Rename indexes back
    op.execute("ALTER INDEX idx_tmdb_reviews_movie_created RENAME TO idx_reviews_movie_created")
    op.execute("ALTER INDEX idx_tmdb_reviews_user_created RENAME TO idx_reviews_user_created")
    
    # Rename table back
    op.rename_table("tmdb_reviews", "reviews")
