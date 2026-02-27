"""Update schema with new ERD structure.

This migration only contains changes applied after:
- 20260206_000001_init
- 20260209_000002_movie_people_and_metrics
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260210_000003"
down_revision = "20260209_000002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Update users table
    op.alter_column('users', 'avatar_url', new_column_name='avatar_text')
    
    # 2. Update movies table
    op.alter_column('movies', 'overview', new_column_name='synopsis')
    op.alter_column('movies', 'release_date', new_column_name='release')
    op.drop_column('movies', 'category')
    op.drop_column('movies', 'release_year')
    
    # 3. Create movie_tags table (rename from movie_keywords)
    op.rename_table('movie_keywords', 'movie_tags')
    op.alter_column('movie_tags', 'keyword', new_column_name='tag')
    op.create_index('ix_movie_tags_movie_tag', 'movie_tags', ['movie_id', 'tag'])
    
    # 4. Update movie_genres index
    op.create_index('ix_movie_genres_movie_genre', 'movie_genres', ['movie_id', 'genre'])
    
    # 5. Update reviews table
    op.alter_column('reviews', 'comment', new_column_name='content')
    op.drop_column('reviews', 'likes_count')
    
    # Add foreign keys to reviews
    op.create_foreign_key(
        'fk_reviews_user_id', 'reviews', 'users',
        ['user_id'], ['id'], ondelete='CASCADE'
    )
    op.create_foreign_key(
        'fk_reviews_movie_id', 'reviews', 'movies',
        ['movie_id'], ['id'], ondelete='CASCADE'
    )
    
    # Add unique constraint for user-movie review
    op.create_unique_constraint('uq_user_movie_review', 'reviews', ['user_id', 'movie_id'])
    op.create_index('ix_reviews_user_movie', 'reviews', ['user_id', 'movie_id'])
    
    # 6. Rename review_comments to comments
    op.rename_table('review_comments', 'comments')
    op.alter_column('comments', 'comment', new_column_name='content')
    
    # Add foreign keys to comments
    op.create_foreign_key(
        'fk_comments_review_id', 'comments', 'reviews',
        ['review_id'], ['id'], ondelete='CASCADE'
    )
    op.create_foreign_key(
        'fk_comments_user_id', 'comments', 'users',
        ['user_id'], ['id'], ondelete='CASCADE'
    )
    
    # 7. Update review_likes table
    op.add_column('review_likes', sa.Column('is_like', sa.Boolean(), nullable=False, server_default='true'))
    
    # Add foreign keys to review_likes
    op.create_foreign_key(
        'fk_review_likes_review_id', 'review_likes', 'reviews',
        ['review_id'], ['id'], ondelete='CASCADE'
    )
    op.create_foreign_key(
        'fk_review_likes_user_id', 'review_likes', 'users',
        ['user_id'], ['id'], ondelete='CASCADE'
    )
    
    # Update unique constraint name
    op.drop_constraint('uq_review_likes', 'review_likes', type_='unique')
    op.create_unique_constraint('uq_review_user_like', 'review_likes', ['review_id', 'user_id'])
    
    # 8. Create taste_analysis table (rename from taste_profiles)
    op.rename_table('taste_profiles', 'taste_analysis')
    op.add_column('taste_analysis', sa.Column('summary_text', sa.Text(), nullable=True))
    op.drop_column('taste_analysis', 'emotion_scores')
    op.drop_column('taste_analysis', 'narrative_traits')
    op.drop_column('taste_analysis', 'ending_preference')
    
    # Add foreign key
    op.create_foreign_key(
        'fk_taste_analysis_user_id', 'taste_analysis', 'users',
        ['user_id'], ['id'], ondelete='CASCADE'
    )
    
    # Update unique constraint name
    op.drop_constraint('uq_taste_profile_user', 'taste_analysis', type_='unique')
    op.create_unique_constraint('uq_taste_analysis_user', 'taste_analysis', ['user_id'])
    
    # 9. Create group_decisions table
    op.create_table(
        'group_decisions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('owner_user_id', sa.String(), nullable=False),
        sa.Column('group_type', sa.String(), nullable=False, comment='personal, friends, family'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['owner_user_id'], ['users.id'], ondelete='CASCADE')
    )
    op.create_index('ix_group_decisions_owner_user_id', 'group_decisions', ['owner_user_id'])
    
    # 10. Create group_members table
    op.create_table(
        'group_members',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('group_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.ForeignKeyConstraint(['group_id'], ['group_decisions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('group_id', 'user_id', name='uq_group_user')
    )
    op.create_index('ix_group_members_group_id', 'group_members', ['group_id'])
    op.create_index('ix_group_members_user_id', 'group_members', ['user_id'])
    
    # 11. Create user_preferences table
    op.create_table(
        'user_preferences',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('preference_vector_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('persona_code', sa.String(), nullable=True),
        sa.Column('boost_tags', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column('penalty_tags', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id', name='uq_user_preferences_user')
    )
    op.create_index('ix_user_preferences_user_id', 'user_preferences', ['user_id'])
    
    # 12. Update movie_vectors table
    op.alter_column('movie_vectors', 'embedding', new_column_name='embedding_vector')
    
    # Add foreign key
    op.create_foreign_key(
        'fk_movie_vectors_movie_id', 'movie_vectors', 'movies',
        ['movie_id'], ['id'], ondelete='CASCADE'
    )
    
    # Update unique constraint name
    op.drop_constraint('uq_movie_vectors_movie', 'movie_vectors', type_='unique')
    op.create_unique_constraint('uq_movie_vectors_movie_id', 'movie_vectors', ['movie_id'])
    
    # 13. Add foreign keys to movie_genres and movie_tags
    op.create_foreign_key(
        'fk_movie_genres_movie_id', 'movie_genres', 'movies',
        ['movie_id'], ['id'], ondelete='CASCADE'
    )
    op.create_foreign_key(
        'fk_movie_tags_movie_id', 'movie_tags', 'movies',
        ['movie_id'], ['id'], ondelete='CASCADE'
    )
    
    # 14. Drop watch_logs table (not in new ERD)
    op.drop_table('watch_logs')


def downgrade() -> None:
    # Reverse all changes
    
    # 14. Recreate watch_logs
    op.create_table(
        'watch_logs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('movie_id', sa.Integer(), nullable=False),
        sa.Column('rating', sa.Numeric(), nullable=False),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False)
    )
    op.create_index('idx_watch_logs_user_created', 'watch_logs', ['user_id', 'created_at'])
    
    # 13. Drop foreign keys from movie_genres and movie_tags
    op.drop_constraint('fk_movie_tags_movie_id', 'movie_tags', type_='foreignkey')
    op.drop_constraint('fk_movie_genres_movie_id', 'movie_genres', type_='foreignkey')
    
    # 12. Revert movie_vectors
    op.drop_constraint('fk_movie_vectors_movie_id', 'movie_vectors', type_='foreignkey')
    op.drop_constraint('uq_movie_vectors_movie_id', 'movie_vectors', type_='unique')
    op.create_unique_constraint('uq_movie_vectors_movie', 'movie_vectors', ['movie_id'])
    op.alter_column('movie_vectors', 'embedding_vector', new_column_name='embedding')
    
    # 11. Drop user_preferences
    op.drop_table('user_preferences')
    
    # 10. Drop group_members
    op.drop_table('group_members')
    
    # 9. Drop group_decisions
    op.drop_table('group_decisions')
    
    # 8. Revert taste_analysis to taste_profiles
    op.drop_constraint('fk_taste_analysis_user_id', 'taste_analysis', type_='foreignkey')
    op.drop_constraint('uq_taste_analysis_user', 'taste_analysis', type_='unique')
    op.create_unique_constraint('uq_taste_profile_user', 'taste_analysis', ['user_id'])
    op.drop_column('taste_analysis', 'summary_text')
    op.add_column('taste_analysis', sa.Column('emotion_scores', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")))
    op.add_column('taste_analysis', sa.Column('narrative_traits', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")))
    op.add_column('taste_analysis', sa.Column('ending_preference', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")))
    op.rename_table('taste_analysis', 'taste_profiles')
    
    # 7. Revert review_likes
    op.drop_constraint('fk_review_likes_user_id', 'review_likes', type_='foreignkey')
    op.drop_constraint('fk_review_likes_review_id', 'review_likes', type_='foreignkey')
    op.drop_constraint('uq_review_user_like', 'review_likes', type_='unique')
    op.create_unique_constraint('uq_review_likes', 'review_likes', ['review_id', 'user_id'])
    op.drop_column('review_likes', 'is_like')
    
    # 6. Revert comments to review_comments
    op.drop_constraint('fk_comments_user_id', 'comments', type_='foreignkey')
    op.drop_constraint('fk_comments_review_id', 'comments', type_='foreignkey')
    op.alter_column('comments', 'content', new_column_name='comment')
    op.rename_table('comments', 'review_comments')
    
    # 5. Revert reviews
    op.drop_index('ix_reviews_user_movie', 'reviews')
    op.drop_constraint('uq_user_movie_review', 'reviews', type_='unique')
    op.drop_constraint('fk_reviews_movie_id', 'reviews', type_='foreignkey')
    op.drop_constraint('fk_reviews_user_id', 'reviews', type_='foreignkey')
    op.add_column('reviews', sa.Column('likes_count', sa.Integer(), nullable=False, server_default='0'))
    op.alter_column('reviews', 'content', new_column_name='comment')
    
    # 4. Revert movie_genres index
    op.drop_index('ix_movie_genres_movie_genre', 'movie_genres')
    
    # 3. Revert movie_tags to movie_keywords
    op.drop_index('ix_movie_tags_movie_tag', 'movie_tags')
    op.alter_column('movie_tags', 'tag', new_column_name='keyword')
    op.rename_table('movie_tags', 'movie_keywords')
    
    # 2. Revert movies
    op.add_column('movies', sa.Column('release_year', sa.Integer(), nullable=True))
    op.add_column('movies', sa.Column('category', sa.String(), nullable=True))
    op.alter_column('movies', 'release', new_column_name='release_date')
    op.alter_column('movies', 'synopsis', new_column_name='overview')
    
    # 1. Revert users
    op.alter_column('users', 'avatar_text', new_column_name='avatar_url')
