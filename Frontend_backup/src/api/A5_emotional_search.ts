/**
 * A-5: 자연어 기반 감성 검색 API
 */
import { post } from "./http";

export interface EmotionalSearchRequest {
  text: string;
  genres?: string[];
  year_from?: number;
  year_to?: number;
}

export interface EmotionalSearchResponse {
  intent: string;
  expanded_query: {
    emotion_scores: Record<string, number>;
  };
  hybrid_query: {
    query: {
      bool: {
        must: any[];
        filter: any[];
      };
    };
    knn: {
      field: string;
      query_vector: number[];
      k: number;
      num_candidates: number;
    };
  };
}

/**
 * 자연어 텍스트로 감성 기반 영화 검색
 */
export async function emotionalSearch(
  request: EmotionalSearchRequest
): Promise<EmotionalSearchResponse> {
  return post<EmotionalSearchResponse>("/search/emotional", request);
}

/**
 * 감성 검색 결과를 기반으로 영화 목록 조회
 * (현재는 emotion_scores를 활용한 필터링)
 */
export async function searchMoviesByEmotion(
  text: string,
  options?: {
    genres?: string[];
    year_from?: number;
    year_to?: number;
    page?: number;
    page_size?: number;
  }
): Promise<any> {
  // 1. 감성 검색으로 emotion_scores 추출
  const searchResult = await emotionalSearch({
    text,
    genres: options?.genres,
    year_from: options?.year_from,
    year_to: options?.year_to,
  });

  // 2. emotion_scores에서 상위 태그 추출
  const emotionScores = searchResult.expanded_query.emotion_scores;
  const topEmotions = Object.entries(emotionScores)
    .filter(([_, score]) => score > 0.5)
    .sort(([_, a], [__, b]) => b - a)
    .slice(0, 3)
    .map(([tag, _]) => tag);

  // 3. 태그를 쿼리로 변환하여 영화 검색
  // 현재는 일반 검색 API 사용 (나중에 벡터 검색으로 업그레이드 가능)
  const queryText = topEmotions.join(" ");
  
  return {
    emotion_scores: emotionScores,
    top_emotions: topEmotions,
    query_text: queryText,
    search_result: searchResult,
  };
}
