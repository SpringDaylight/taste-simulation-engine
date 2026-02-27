"""add survey fields to user_preferences

Revision ID: 20260225_000019
Revises: 20260223_000018
Create Date: 2026-02-25

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision = '20260225_000019'
down_revision = '20260223_000018'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add survey-related columns to user_preferences table
    op.add_column('user_preferences', sa.Column('favorite_genres', JSONB, nullable=True, comment='좋아하는 장르 리스트'))
    op.add_column('user_preferences', sa.Column('disliked_genres', JSONB, nullable=True, comment='싫어하는 장르 리스트'))
    op.add_column('user_preferences', sa.Column('viewing_context', sa.String(), nullable=True, comment='영화 감상 맥락 (혼자/연인/가족/자기전/주말)'))
    op.add_column('user_preferences', sa.Column('preferred_vibe', sa.String(), nullable=True, comment='선호 분위기 (가볍고 유쾌한/감동적/충격적 등)'))
    op.add_column('user_preferences', sa.Column('interest_keywords', JSONB, nullable=True, comment='관심 키워드 리스트'))
    op.add_column('user_preferences', sa.Column('preferred_origin', sa.String(), nullable=True, comment='선호 국적 (한국/미국/일본/유럽/고전)'))


def downgrade() -> None:
    # Remove survey-related columns
    op.drop_column('user_preferences', 'preferred_origin')
    op.drop_column('user_preferences', 'interest_keywords')
    op.drop_column('user_preferences', 'preferred_vibe')
    op.drop_column('user_preferences', 'viewing_context')
    op.drop_column('user_preferences', 'disliked_genres')
    op.drop_column('user_preferences', 'favorite_genres')
