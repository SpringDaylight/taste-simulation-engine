/**
 * LLM 기반 영화 추천 API
 */
import { post } from './http';

export interface RecommendRequest {
  user_input: string;
  top_k?: number;
  candidate_pool_size?: number;
  genres?: string[];
  year_from?: number;
  year_to?: number;
  use_orchestrator?: boolean; // 오케스트레이터 사용 여부
}

export interface Movie {
  movie_id: number;
  title: string;
  genres: string[];
  release_year: number;
  similarity_score: number;  // 프론트 호환성 (final_score와 동일)
  final_score?: number;  // 최종 점수 (가중치 + 보너스)
  weighted_score?: number;  // 가중치 적용 점수
  keyword_score?: number;  // 키워드 점수
  emotion_score?: number;  // 감성 점수
  sources?: string[];  // 검색 소스 (keyword, vector)
  detail_url: string;
  poster_url?: string;
  rating?: number;
  synopsis?: string;  // 시놉시스
  reason?: string; // 개별 추천 이유 (오케스트레이터 모드)
  is_selected?: boolean;  // 최종 선택 여부
  not_selected_reason?: string;  // 선택되지 않은 이유
  satisfaction_probability?: number;  // 만족도 확률
}

export interface RecommendResponse {
  recommendations: Movie[];
  explanation: string;
  candidates_count: number;
  method?: string; // 'basic' or 'orchestrator'
  usage?: {
    input_tokens: number;
    output_tokens: number;
  };
  keyword_candidates?: Movie[];  // 키워드 후보군
  vector_candidates?: Movie[];  // 벡터 후보군
  keyword_weight?: number;  // 키워드 가중치
  emotion_weight?: number;  // 감성 가중치
}

export interface ExplainRequest {
  user_input: string;
  movie_title: string;
  movie_synopsis?: string;
  genres?: string[];
  keyword_score?: number;
  emotion_score?: number;
  final_score?: number;
}

export interface ExplainResponse {
  explanation: string;
  movie_title: string;
}

export interface SatisfactionRequest {
  movie_id: number;
  user_id?: string;  // ✅ Optional: 하위 호환성을 위해 유지, JWT 인증 시 불필요
}

export interface SatisfactionResponse {
  movie_id: number;
  satisfaction_probability: number;
  confidence?: number;
  breakdown?: {
    emotion_similarity: number;
    narrative_similarity: number;
    ending_similarity: number;
    boost_score: number;
    dislike_penalty: number;
    top_factors: string[];
  };
  user_id?: number;
}

/**
 * LLM 기반 영화 추천
 */
export async function recommendMovies(
  request: RecommendRequest
): Promise<RecommendResponse> {
  return post<RecommendResponse>('/api/llm/recommend', request);
}

/**
 * 특정 영화 추천 이유 상세 설명
 */
export async function explainRecommendation(
  request: ExplainRequest
): Promise<ExplainResponse> {
  return post<ExplainResponse>('/api/llm/explain', request);
}

/**
 * 사용자 취향과 영화 특성 간의 만족도 확률 계산
 */
export async function calculateSatisfaction(
  request: SatisfactionRequest
): Promise<SatisfactionResponse> {
  console.log('📤 [calculateSatisfaction] Sending request:', request);
  const response = await post<SatisfactionResponse>('/api/llm/satisfaction', request);
  console.log('📥 [calculateSatisfaction] Received response:', response);
  return response;
}
