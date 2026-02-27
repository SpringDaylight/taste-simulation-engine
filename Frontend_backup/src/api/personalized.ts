/**
 * 개인 맞춤 추천 API
 * 홈 화면용 - 백엔드에서 모든 계산 완료
 */
import { get } from "./http";

export interface PersonalizedMovie {
  movie_id: number;
  title: string;
  poster_url: string | null;
  genres: string[];
  release_year: number | null;
  avg_rating: number | null;
  synopsis: string | null;
  satisfaction_probability: number; // 0.0 ~ 1.0
  match_rate: number; // 0 ~ 100
  detail_url: string;
}

export interface PersonalizedRecommendResponse {
  recommendations: PersonalizedMovie[];
  total: number;
  user_id: string;
  has_preference: boolean;
}

/**
 * 개인 맞춤 추천 가져오기
 * 
 * @param top_k 추천할 영화 개수 (기본 12개)
 * @param candidate_pool_size 후보 풀 크기 (기본 100개)
 * @returns 정렬된 추천 영화 리스트
 */
export const getPersonalizedRecommendations = async (
  top_k: number = 12,
  candidate_pool_size: number = 100
): Promise<PersonalizedRecommendResponse> => {
  return get<PersonalizedRecommendResponse>(
    "/api/personalized/recommendations",
    {
      top_k,
      candidate_pool_size,
    }
  );
};

/**
 * 빠른 개인 맞춤 추천 (홈 화면 초기 로딩용)
 * 
 * 후보 50개, 추천 12개로 고정
 * 
 * @returns 정렬된 추천 영화 리스트
 */
export const getQuickRecommendations = async (): Promise<PersonalizedRecommendResponse> => {
  return get<PersonalizedRecommendResponse>(
    "/api/personalized/recommendations/quick"
  );
};
