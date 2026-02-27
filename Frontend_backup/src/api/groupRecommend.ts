/**
 * 그룹 영화 추천 API (커밋 559354d 기능 통합)
 */
import { post } from './http';

export interface GroupUser {
  user_id: string;
  name: string;
  text?: string;
  likes?: string[];
  dislikes?: string[];
  profile?: any;
}

export interface GroupRecommendRequest {
  users: GroupUser[];
  top_k?: number;
  candidate_k?: number;
  strategy?: 'mean' | 'min' | 'median' | 'trimmed_mean';
  genres?: string[];
  year_from?: number;
  year_to?: number;
  use_bedrock?: boolean;
}

export interface TagDetail {
  tag: string;
  match_score: number;
  user_score?: number;
  movie_score?: number;
}

export interface UserDetail {
  user_id: string;
  name: string;
  probability: number;
  top_factors: string[];
  emotion_tags: TagDetail[];
  narrative_tags: TagDetail[];
  ending_tags: TagDetail[];
  dislike_penalty: number;
  boost_score: number;
  explanation: string;
}

export interface RecommendedMovie {
  movie_id: number;
  title: string;
  genres: string[];
  release_year: number;
  poster_url?: string | null;
  group_score: number;
  prefilter_score: number;
  per_user_detail?: UserDetail[];
}

export interface GroupRecommendResponse {
  strategy: string;
  topk: RecommendedMovie[];
  candidates_count: number;
  filters?: any;
}

/**
 * 그룹 영화 추천 (LLM 기반 설명 포함)
 */
export async function recommendGroupMovies(
  request: GroupRecommendRequest
): Promise<GroupRecommendResponse> {
  return post<GroupRecommendResponse>('/api/group/recommend-v2', request);
}
