/**
 * Watched Movies API
 */
import { del, get, post } from "./http";

export interface WatchedMovie {
  id: number;
  user_id: string;
  movie_id: number;
  movie_title?: string | null;
  poster_url?: string | null;
  created_at: string;
  title?: string | null;
  watched_at?: string;
  genres?: string[] | null;
}

export interface WatchedMovieListResponse {
  items: WatchedMovie[];
  total: number;
}

export interface SaveWatchedMovieRequest {
  movie_id: number;
}

const LOCAL_WATCHED_KEY = "mw_local_watched";

const buildLocalWatchedKey = (userId: string) => `${LOCAL_WATCHED_KEY}:${userId}`;

const parseLocalWatched = (raw: string | null): WatchedMovie[] => {
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
};

export function getLocalWatchedMovies(userId: string): WatchedMovie[] {
  if (!userId || typeof window === "undefined") return [];
  const current = parseLocalWatched(localStorage.getItem(buildLocalWatchedKey(userId)));
  return current.map((item) => ({
    genres: Array.isArray(item.genres) ? item.genres : null,
    ...item,
  }));
}

export function saveLocalWatchedMovies(userId: string, items: WatchedMovie[]): void {
  if (!userId || typeof window === "undefined") return;
  localStorage.setItem(buildLocalWatchedKey(userId), JSON.stringify(items));
}

export function upsertLocalWatchedMovie(
  userId: string,
  movie: {
    movie_id: number;
    title?: string | null;
    poster_url?: string | null;
    genres?: string[] | null;
  }
): WatchedMovie[] {
  if (!userId) return [];
  const current = getLocalWatchedMovies(userId);
  const next = [
    {
      id: Date.now(),
      user_id: userId,
      movie_id: movie.movie_id,
      movie_title: movie.title ?? null,
      title: movie.title ?? null,
      poster_url: movie.poster_url ?? null,
      genres: movie.genres ?? null,
      watched_at: new Date().toISOString(),
      created_at: new Date().toISOString(),
    },
    ...current.filter((item) => Number(item.movie_id) !== Number(movie.movie_id)),
  ];
  saveLocalWatchedMovies(userId, next);
  return next;
}

export function removeLocalWatchedMovie(userId: string, movieId: number): WatchedMovie[] {
  if (!userId) return [];
  const current = getLocalWatchedMovies(userId);
  const next = current.filter((item) => Number(item.movie_id) !== Number(movieId));
  saveLocalWatchedMovies(userId, next);
  return next;
}

/**
 * Get current user's watched movies
 */
export function getCurrentUserWatchedMovies(
  params?: {
    page?: number;
    page_size?: number;
  }
): Promise<WatchedMovieListResponse> {
  return get<WatchedMovieListResponse>("/api/users/me/watched", params);
}

/**
 * Save watched movie for current user
 */
export function saveCurrentUserWatchedMovie(
  data: SaveWatchedMovieRequest
): Promise<WatchedMovie> {
  return post<WatchedMovie>("/api/users/me/watched", data);
}

/**
 * Delete watched movie for current user
 */
export function deleteCurrentUserWatchedMovie(
  movieId: number
): Promise<{ message: string }> {
  return del<{ message: string }>(`/api/users/me/watched/${movieId}`);
}
