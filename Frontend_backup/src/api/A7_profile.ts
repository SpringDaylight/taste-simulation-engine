/**
 * User Profile API
 */
import { del, get, post, put } from './http';

// Types
export interface User {
  id: string;
  name: string;
  user_id?: string | null;
  nickname?: string | null;
  email?: string | null;
  birth_date?: string | null;
  gender?: string | null;
  avatar_text: string | null;
  level?: number | null;
  exp?: number | null;
  popcorn?: number | null;
  last_roulette_date?: string | null;
  created_at: string;
}

export interface Review {
  id: number;
  user_id: string;
  movie_id: number;
  rating: number;
  content: string | null;
  created_at: string;
  likes_count: number;
  dislikes_count?: number;
  comments_count: number;
  is_public?: boolean;
}

export interface ReviewListResponse {
  reviews: Review[];
  total: number;
}

export interface TasteAnalysis {
  user_id: string;
  summary_text: string | null;
  updated_at: string;
}

export interface CreateUserRequest {
  id: string;
  name: string;
  avatar_text?: string;
}

export interface UpdateUserRequest {
  name?: string;
  avatar_text?: string;
  nickname?: string;
  email?: string;
  birth_date?: string | null;
  gender?: string | null;
}

// API Functions

/**
 * Get current user info
 * MW-API-009
 */
export function getCurrentUser(): Promise<User> {
  return get<User>('/api/users/me');
}

/**
 * Create a new user
 */
export function createUser(data: CreateUserRequest): Promise<User> {
  return post<User>('/api/users', data);
}

/**
 * Update current user
 */
export function updateCurrentUser(
  data: UpdateUserRequest
): Promise<User> {
  return put<User>('/api/users/me', data);
}

/**
 * Delete current user account
 * MW-API-??? (users/me delete)
 */
export function deleteCurrentUser(): Promise<{ message: string }> {
  return del('/api/users/me');
}

/**
 * Get current user's reviews
 * MW-API-010
 */
export function getCurrentUserReviews(
  params?: {
    page?: number;
    page_size?: number;
  }
): Promise<ReviewListResponse> {
  return get<ReviewListResponse>('/api/users/me/reviews', params);
}

/**
 * Get user's taste analysis
 * MW-API-011
 */
export function getUserTasteAnalysis(): Promise<TasteAnalysis> {
  return get<TasteAnalysis>('/api/users/me/taste-analysis');
}

/**
 * Get user by ID
 */
export function getUser(userId: string): Promise<User> {
  return get<User>(`/api/users/${userId}`);
}
