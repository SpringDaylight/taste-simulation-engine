/**
 * API Index - Export all API modules
 */

// HTTP Client
export * from './http';

// Movies API
export {
  getMovies,
  getMovie,
  getMovieReviews,
  createMovieReview,
  searchMovies,
  getMoviesByGenre,
  getPopularMovies,
  getLatestMovies,
} from './A2_movies';
export type {
  Movie,
  MovieListResponse,
  Review as MovieReview,
  ReviewListResponse as MovieReviewListResponse,
  CreateReviewRequest,
} from './A2_movies';

// Reviews API
export {
  createReview,
  getReview,
  updateReview,
  deleteReview,
  toggleReviewLike,
  getReviewComments,
  createReviewComment,
  likeReview,
  dislikeReview,
} from './A6_reviews';
export type {
  Review as ReviewDetail,
  Comment,
  CreateReviewRequest as CreateReviewPayload,
  UpdateReviewRequest,
  CreateCommentRequest,
  MessageResponse,
} from './A6_reviews';

// Profile/User API
export {
  getCurrentUser,
  createUser,
  updateCurrentUser,
  getCurrentUserReviews,
  getUserTasteAnalysis,
  getUser,
} from './A7_profile';
export type {
  User,
  Review as UserReview,
  ReviewListResponse as UserReviewListResponse,
  TasteAnalysis,
  CreateUserRequest,
  UpdateUserRequest,
} from './A7_profile';

// Watched Movies API
export {
  getCurrentUserWatchedMovies,
  saveCurrentUserWatchedMovie,
  deleteCurrentUserWatchedMovie,
} from './A8_watched';
export type {
  WatchedMovie,
  WatchedMovieListResponse,
  SaveWatchedMovieRequest,
} from './A8_watched';

// Auth API
export * from './auth';

// ML API
export {
  analyzePreference,
  vectorizeMovie,
  predictSatisfaction,
  explainPrediction,
  emotionalSearch,
  simulateGroup,
  getTasteMap,
  getMovieRecommendation,
} from './ml';
export type {
  UserProfile,
  MovieProfile,
  SatisfactionPrediction,
  PredictionExplanation,
  GroupSimulationResult,
  TasteMapResponse,
  AnalyzePreferenceRequest,
  MovieVectorRequest,
  PredictSatisfactionRequest,
  ExplainPredictionRequest,
  EmotionalSearchRequest,
  GroupSimulateRequest,
  TasteMapRequest,
} from './ml';

// Re-export for convenience
import * as moviesApi from './A2_movies';
import * as reviewsApi from './A6_reviews';
import * as profileApi from './A7_profile';
import * as watchedApi from './A8_watched';
import * as authApi from './auth';
import * as mlApi from './ml';

export const api = {
  movies: moviesApi,
  reviews: reviewsApi,
  profile: profileApi,
  watched: watchedApi,
  auth: authApi,
  ml: mlApi,
};

export default api;
