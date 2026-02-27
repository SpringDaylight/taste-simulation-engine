/**
 * Reviews API
 */
import { get, post, put, del } from './http';

// Types
export interface Review {
  id: number;
  user_id: string;
  movie_id: number;
  rating: number;
  content: string | null;
  keywords?: string[];
  created_at: string;
  likes_count: number;
  dislikes_count?: number;
  comments_count: number;
  is_public?: boolean;
}

export interface Comment {
  id: number;
  review_id: number;
  user_id: string;
  content: string;
  created_at: string;
  likes_count?: number;
  dislikes_count?: number;
}

export interface UpdateReviewRequest {
  rating?: number;
  content?: string | null;
  keywords?: string[];
  is_public?: boolean;
}

export interface CreateReviewRequest {
  movie_id: number;
  rating: number;
  content?: string | null;
  keywords?: string[];
  is_public?: boolean;
}

export interface CreateCommentRequest {
  content: string;
  is_public?: boolean;
}

export interface MessageResponse {
  message: string;
}

export interface LikeToggleResponse {
  message: string;
  review_id: number;
  likes_count: number;
  dislikes_count: number;
}

export interface CommentLikeToggleResponse {
  message: string;
  comment_id: number;
  likes_count: number;
  dislikes_count: number;
}

// API Functions

/**
 * Create a review
 * MW-API-004
 */
export function createReview(
  data: CreateReviewRequest
): Promise<Review> {
  return post<Review>('/api/reviews', data);
}

/**
 * Get review detail by ID
 * MW-API-006
 */
export function getReview(reviewId: number): Promise<Review> {
  return get<Review>(`/api/reviews/${reviewId}`);
}

/**
 * Update a review
 * MW-API-005
 */
export function updateReview(
  reviewId: number,
  data: UpdateReviewRequest
): Promise<Review> {
  return put<Review>(`/api/reviews/${reviewId}`, data);
}

/**
 * Delete a review
 */
export function deleteReview(reviewId: number): Promise<MessageResponse> {
  return del<MessageResponse>(`/api/reviews/${reviewId}`);
}

/**
 * Toggle like on a review
 * MW-API-007
 */
export function toggleReviewLike(
  reviewId: number,
  isLike = true
): Promise<LikeToggleResponse> {
  return post<LikeToggleResponse>(
    `/api/reviews/${reviewId}/likes`,
    undefined,
    { is_like: isLike }
  );
}

/**
 * Toggle like on a comment
 */
export function toggleCommentLike(
  commentId: number,
  isLike = true
): Promise<CommentLikeToggleResponse> {
  return post<CommentLikeToggleResponse>(
    `/api/reviews/comments/${commentId}/likes`,
    undefined,
    { is_like: isLike }
  );
}

/**
 * Get comments for a review
 * MW-API-008
 */
export function getReviewComments(
  reviewId: number,
  params?: {
    skip?: number;
    limit?: number;
  }
): Promise<Comment[]> {
  return get<Comment[]>(`/api/reviews/${reviewId}/comments`, params);
}

/**
 * Create a comment on a review
 * MW-API-008
 */
export function createReviewComment(
  reviewId: number,
  data: CreateCommentRequest
): Promise<Comment> {
  const payload = { is_public: true, ...data, review_id: reviewId };
  return post<Comment>(
    `/api/reviews/${reviewId}/comments`,
    payload
  );
}


/**
 * Delete a comment
 */
export function deleteReviewComment(
  commentId: number
): Promise<MessageResponse> {
  return del<MessageResponse>(`/api/reviews/comments/${commentId}`);
}


/**
 * Update a comment
 */
export function updateReviewComment(
  commentId: number,
  data: { content: string }
): Promise<Comment> {
  return put<Comment>(`/api/reviews/comments/${commentId}`, data);
}

/**
 * Like a review (shorthand)
 */
export function likeReview(reviewId: number): Promise<LikeToggleResponse> {
  return toggleReviewLike(reviewId, true);
}

/**
 * Dislike a review (shorthand)
 */
export function dislikeReview(reviewId: number): Promise<LikeToggleResponse> {
  return toggleReviewLike(reviewId, false);
}
