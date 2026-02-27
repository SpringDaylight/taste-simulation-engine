/**
 * Movies API
 */
import { get, post } from './http';

// Types
export interface Movie {
  id: number;
  title: string;
  avg_rating: number | null;
  review_count?: number;
  reviews_count?: number;
  release: string | null;
  runtime: number | null;
  synopsis: string | null;
  poster_url: string | null;
  created_at: string;
  genres: string[];
  tags: string[];
}

export interface MovieListResponse {
  movies: Movie[];
  total: number;
  page: number;
  page_size: number;
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
  is_public?: boolean;
  comments_count: number;
}

export interface ReviewListResponse {
  reviews: Review[];
  total: number;
}

export interface CreateReviewRequest {
  rating: number;
  content?: string;
}

// API Functions

/**
 * Get movies list with filters
 * MW-API-001
 */
export function getMovies(params?: {
  query?: string;
  genres?: string;
  category?: string;
  sort?: 'latest' | 'popular' | 'rating' | 'title';
  runtime_min?: number;
  runtime_max?: number;
  runtime_ranges?: string;
  year_min?: number;
  year_max?: number;
  year_ranges?: string;
  page?: number;
  page_size?: number;
}): Promise<MovieListResponse> {
  return get<MovieListResponse>('/api/movies', params);
}

/**
 * Get movie detail by ID
 * MW-API-002
 */
export function getMovie(movieId: number): Promise<Movie> {
  return get<Movie>(`/api/movies/${movieId}`);
}

/**
 * Get reviews for a specific movie
 * MW-API-003
 */
export function getMovieReviews(
  movieId: number,
  params?: {
    page?: number;
    page_size?: number;
    user_id?: string;
  }
): Promise<ReviewListResponse> {
  return get<ReviewListResponse>(`/api/movies/${movieId}/reviews`, params);
}

/**
 * Create a review for a movie
 * MW-API-004
 */
export function createMovieReview(
  movieId: number,
  userId: string,
  data: CreateReviewRequest
): Promise<Review> {
  return post<Review>(
    '/api/reviews',
    {
      movie_id: movieId,
      ...data,
    },
    { user_id: userId }
  );
}

/**
 * Search movies by query
 */
export function searchMovies(query: string, page = 1): Promise<MovieListResponse> {
  return getMovies({ query, page });
}

/**
 * Get movies by genre
 */
export function getMoviesByGenre(
  genre: string,
  sort: 'latest' | 'popular' | 'rating' = 'popular',
  page = 1
): Promise<MovieListResponse> {
  return getMovies({ genres: genre, sort, page });
}

/**
 * Get popular movies
 */
export function getPopularMovies(page = 1): Promise<MovieListResponse> {
  return getMovies({ sort: 'popular', page });
}

/**
 * Get latest movies
 */
export function getLatestMovies(page = 1): Promise<MovieListResponse> {
  return getMovies({ sort: 'latest', page });
}
