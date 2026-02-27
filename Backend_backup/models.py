"""
Database models for Movie Recommendation System
Based on ERD from 프로젝트 착수 보고서
"""
from sqlalchemy import (
    Column, Date, DateTime, Integer, String, Text, Numeric, Float,
    ForeignKey, UniqueConstraint, Index, Boolean
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime

from db import Base


class User(Base):
    """사용자 테이블"""
    __tablename__ = "users"

    id = Column(String, primary_key=True)
    user_id = Column(String, unique=True, index=True, nullable=True)
    name = Column(String, nullable=False)
    nickname = Column(String, unique=True, index=True, nullable=True)
    email = Column(String, unique=True, index=True, nullable=True)
    password_hash = Column(String, nullable=True)
    birth_date = Column(Date, nullable=True, comment="User birth date")
    gender = Column(String, nullable=True, comment="User gender")
    avatar_text = Column(String, nullable=True, comment="씁쓸한 로맨스, 슬픈 코미디 같은 문구")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Gamification Fields
    level = Column(Integer, default=1)
    exp = Column(Integer, default=0)
    popcorn = Column(Integer, default=0)
    main_flavor = Column(String, default="Sweet")
    stage = Column(String, default="Egg")
    last_feeding_date = Column(String, nullable=True) # YYYY-MM-DD
    last_question_date = Column(String, nullable=True) # YYYY-MM-DD
    current_question_index = Column(Integer, default=0)
    last_roulette_date = Column(String, nullable=True) # YYYY-MM-DD

    # Relationships
    reviews = relationship("Review", back_populates="user", cascade="all, delete-orphan")
    review_likes = relationship("ReviewLike", back_populates="user", cascade="all, delete-orphan")
    comment_likes = relationship("CommentLike", back_populates="user", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="user", cascade="all, delete-orphan")
    taste_analysis = relationship("TasteAnalysis", back_populates="user", uselist=False, cascade="all, delete-orphan")
    group_decisions = relationship("GroupDecision", back_populates="owner", cascade="all, delete-orphan")
    group_memberships = relationship("GroupMember", back_populates="user", cascade="all, delete-orphan")
    watched_movies = relationship("WatchedMovie", back_populates="user", cascade="all, delete-orphan")
    
    # Gamification Relationships
    flavor_stats = relationship("FlavorStat", back_populates="user", cascade="all, delete-orphan")
    inventory = relationship("ThemeInventory", back_populates="user", cascade="all, delete-orphan")
    history = relationship("QuestionHistory", back_populates="user", cascade="all, delete-orphan")
    auth_accounts = relationship("UserAuth", back_populates="user", cascade="all, delete-orphan")
    roulette_rewards = relationship("RouletteReward", back_populates="user", cascade="all, delete-orphan")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")


class UserAuth(Base):
    """Social auth accounts"""
    __tablename__ = "user_auth"

    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    provider = Column(String, nullable=False)
    provider_user_id = Column(String, nullable=False)
    email = Column(String, nullable=True)
    connected_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="auth_accounts")

    __table_args__ = (
        UniqueConstraint("provider", "provider_user_id", name="uq_user_auth_provider_user"),
        Index("ix_user_auth_provider_user", "provider", "provider_user_id"),
    ) 


class RefreshToken(Base):
    """Refresh token storage"""
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String, nullable=False, unique=True, index=True)
    jti = Column(String, nullable=False, unique=True, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="refresh_tokens")


class Movie(Base):
    """영화 메타데이터 테이블"""
    __tablename__ = "movies"

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False, index=True)
    release = Column(Date, nullable=True, comment="개봉일")
    runtime = Column(Integer, nullable=True, comment="러닝타임(분)")
    synopsis = Column(Text, nullable=True, comment="시놉시스")
    poster_url = Column(String, nullable=True)
    keywords = Column(JSONB, nullable=True)
    avg_rating = Column(Numeric(2, 1), nullable=True, comment="Average rating (0.5 steps)")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    genres = relationship("MovieGenre", back_populates="movie", cascade="all, delete-orphan")
    tags = relationship("MovieTag", back_populates="movie", cascade="all, delete-orphan")
    reviews = relationship("Review", back_populates="movie", cascade="all, delete-orphan")
    watched_by = relationship("WatchedMovie", back_populates="movie", cascade="all, delete-orphan")


class MovieGenre(Base):
    """영화 장르 (다대다 분리)"""
    __tablename__ = "movie_genres"

    id = Column(Integer, primary_key=True)
    movie_id = Column(Integer, ForeignKey("movies.id", ondelete="CASCADE"), nullable=False, index=True)
    genre = Column(String, nullable=False, comment="드라마, 로맨스, SF, 스릴러 등")

    # Relationships
    movie = relationship("Movie", back_populates="genres")

    __table_args__ = (
        Index('ix_movie_genres_movie_genre', 'movie_id', 'genre'),
    )


class MovieTag(Base):
    """영화 정성 태그 (정서/서사/여운)"""
    __tablename__ = "movie_tags"

    id = Column(Integer, primary_key=True)
    movie_id = Column(Integer, ForeignKey("movies.id", ondelete="CASCADE"), nullable=False, index=True)
    tag = Column(String, nullable=False, comment="우울, 따뜻, 긴장, 성장, 관계, 여운 김 등")

    # Relationships
    movie = relationship("Movie", back_populates="tags")

    __table_args__ = (
        Index('ix_movie_tags_movie_tag', 'movie_id', 'tag'),
    )


class TMDBReview(Base):
    """TMDB API에서 가져온 리뷰 (ML 학습용)"""
    __tablename__ = "tmdb_reviews"

    id = Column(Integer, primary_key=True)
    movie_id = Column(Integer, nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)
    rating = Column(Numeric, nullable=False)
    comment = Column(Text, nullable=True)
    likes_count = Column(Integer, nullable=False, server_default="0")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index('idx_tmdb_reviews_movie_created', 'movie_id', 'created_at'),
        Index('idx_tmdb_reviews_user_created', 'user_id', 'created_at'),
    )


class Review(Base):
    """사용자 감상 기록 (리뷰)"""
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    movie_id = Column(Integer, ForeignKey("movies.id", ondelete="CASCADE"), nullable=False, index=True)
    rating = Column(Numeric(2, 1), nullable=False, comment="0.5~5.0, 0.5 단위")
    content = Column(Text, nullable=True)
    keywords = Column(JSONB, nullable=True, default=list, comment="감상 키워드 태그 목록")
    is_public = Column(Boolean, nullable=False, default=True, comment="True=공개, False=비공개")
    likes_count = Column(Integer, nullable=False, default=0, comment="좋아요 총합 캐시")
    dislikes_count = Column(Integer, nullable=False, default=0, comment="싫어요 총합 캐시")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="reviews")
    movie = relationship("Movie", back_populates="reviews")
    likes = relationship("ReviewLike", back_populates="review", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="review", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint('user_id', 'movie_id', name='uq_user_movie_review'),
        Index('ix_reviews_user_movie', 'user_id', 'movie_id'),
    )


class Comment(Base):
    """리뷰 댓글"""
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True)
    review_id = Column(Integer, ForeignKey("reviews.id", ondelete="CASCADE"), nullable=False, index=True)
    parent_comment_id = Column(Integer, ForeignKey("comments.id", ondelete="CASCADE"), nullable=True, index=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    is_public = Column(Boolean, nullable=False, default=True, comment="True=공개, False=비공개")
    likes_count = Column(Integer, nullable=False, default=0, comment="좋아요 총합 캐시")
    dislikes_count = Column(Integer, nullable=False, default=0, comment="싫어요 총합 캐시")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    review = relationship("Review", back_populates="comments")
    user = relationship("User", back_populates="comments")
    likes = relationship("CommentLike", back_populates="comment", cascade="all, delete-orphan")
    parent = relationship("Comment", remote_side=[id], backref="replies")


class ReviewLike(Base):
    """리뷰 좋아요"""
    __tablename__ = "review_likes"

    id = Column(Integer, primary_key=True)
    review_id = Column(Integer, ForeignKey("reviews.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    is_like = Column(Boolean, nullable=False, default=True, comment="True=좋아요, False=싫어요")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    review = relationship("Review", back_populates="likes")
    user = relationship("User", back_populates="review_likes")

    __table_args__ = (
        UniqueConstraint('review_id', 'user_id', name='uq_review_user_like'),
    )


class CommentLike(Base):
    """사용자 댓글 좋아요"""
    __tablename__ = "comment_likes"

    id = Column(Integer, primary_key=True)
    comment_id = Column(Integer, ForeignKey("comments.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    is_like = Column(Boolean, nullable=False, default=True, comment="True=좋아요, False=싫어요")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    comment = relationship("Comment", back_populates="likes")
    user = relationship("User", back_populates="comment_likes")

    __table_args__ = (
        UniqueConstraint("comment_id", "user_id", name="uq_comment_user_like"),
    )


class TasteAnalysis(Base):
    """취향 분석 결과 (LLM 기반 파생 데이터)"""
    __tablename__ = "taste_analysis"

    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    summary_text = Column(Text, nullable=True, comment="당신은 관계 중심 서사와 잔잔하지만 여운이 긴 영화를 선호합니다.")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="taste_analysis")


class GroupDecision(Base):
    """같이 정하기 - 그룹"""
    __tablename__ = "group_decisions"

    id = Column(Integer, primary_key=True)
    owner_user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    group_type = Column(String, nullable=False, comment="personal, friends, family")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    owner = relationship("User", back_populates="group_decisions")
    members = relationship("GroupMember", back_populates="group", cascade="all, delete-orphan")


class GroupMember(Base):
    """그룹 멤버"""
    __tablename__ = "group_members"

    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey("group_decisions.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Relationships
    group = relationship("GroupDecision", back_populates="members")
    user = relationship("User", back_populates="group_memberships")

    __table_args__ = (
        UniqueConstraint('group_id', 'user_id', name='uq_group_user'),
    )


# ============================================
# 벡터 데이터 (파생 데이터, ERD 외부)
# ============================================

class UserPreference(Base):
    """사용자 취향 벡터 (DynamoDB 대신 PostgreSQL 사용)"""
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    preference_vector_json = Column(JSONB, nullable=False, default=dict, comment="emotion_scores, narrative_traits, ending_preference")
    persona_code = Column(String, nullable=True, comment="사용자 페르소나 코드")
    boost_tags = Column(JSONB, nullable=False, default=list, comment="좋아하는 태그 리스트")
    dislike_tags = Column(JSONB, nullable=False, default=list, comment="제외/비선호 태그 리스트")
    penalty_tags = Column(JSONB, nullable=False, default=list, comment="싫어하는 태그 리스트")
    
    # Survey fields
    favorite_genres = Column(JSONB, nullable=True, default=list, comment="좋아하는 장르 리스트")
    disliked_genres = Column(JSONB, nullable=True, default=list, comment="싫어하는 장르 리스트")
    viewing_context = Column(String, nullable=True, comment="영화 감상 맥락 (혼자/연인/가족/자기전/주말)")
    preferred_vibe = Column(String, nullable=True, comment="선호 분위기 (가볍고 유쾌한/감동적/충격적 등)")
    interest_keywords = Column(JSONB, nullable=True, default=list, comment="관심 키워드 리스트")
    preferred_origin = Column(String, nullable=True, comment="선호 국적 (한국/미국/일본/유럽/고전)")
    
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class MovieVector(Base):
    """영화 특성 벡터 (OpenSearch 대신 PostgreSQL 사용)"""
    __tablename__ = "movie_vectors"

    id = Column(Integer, primary_key=True)
    movie_id = Column(Integer, ForeignKey("movies.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    emotion_scores = Column(JSONB, nullable=False, default=dict, comment="감정 태그 점수")
    narrative_traits = Column(JSONB, nullable=False, default=dict, comment="서사 특성 점수")
    direction_mood = Column(JSONB, nullable=False, default=dict, comment="연출/분위기 점수")
    character_relationship = Column(JSONB, nullable=False, default=dict, comment="캐릭터 관계 점수")
    ending_preference = Column(JSONB, nullable=False, default=dict, comment="결말 선호도")
    embedding_text = Column(Text, nullable=True, comment="임베딩 생성용 텍스트")
    embedding_vector = Column(JSONB, nullable=True, default=list, comment="임베딩 벡터 (향후 벡터 검색용)")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


# ============================================
# Gamification Models
# ============================================

class FlavorStat(Base):
    __tablename__ = 'flavor_stats'

    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey('users.id', ondelete="CASCADE"), nullable=False)
    flavor_name = Column(String, nullable=False)
    score = Column(Integer, default=0)

    user = relationship("User", back_populates="flavor_stats")

    __table_args__ = (UniqueConstraint('user_id', 'flavor_name', name='_user_flavor_uc'),)


class ThemeInventory(Base):
    __tablename__ = 'theme_inventory'

    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey('users.id', ondelete="CASCADE"), nullable=False)
    
    theme_id = Column(String, nullable=False) # e.g., 'dark', 'pink'
    is_applied = Column(Boolean, default=False)
    acquired_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="inventory")


class QuestionHistory(Base):
    __tablename__ = 'question_history'

    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey('users.id', ondelete="CASCADE"), nullable=False)
    
    date = Column(String, nullable=False) # YYYY-MM-DD
    question = Column(String, nullable=False)
    answer = Column(Text, nullable=False)

    user = relationship("User", back_populates="history")


class WatchedMovie(Base):
    """User watched movies"""
    __tablename__ = "watched_movies"

    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    movie_id = Column(Integer, ForeignKey("movies.id", ondelete="CASCADE"), nullable=False, index=True)
    watched_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="watched_movies")
    movie = relationship("Movie", back_populates="watched_by")

    __table_args__ = (
        UniqueConstraint("user_id", "movie_id", name="uq_user_movie_watched"),
        Index("ix_watched_movies_user_movie", "user_id", "movie_id"),
    )


class RouletteReward(Base):
    """Daily roulette rewards"""
    __tablename__ = "roulette_rewards"

    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    item = Column(String, nullable=False)
    popcorn_gain = Column(Integer, nullable=False, default=0)
    exp_gain = Column(Integer, nullable=False, default=0)
    rewarded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="roulette_rewards")

    __table_args__ = (
        Index("ix_roulette_rewards_user_rewarded", "user_id", "rewarded_at"),
    )
