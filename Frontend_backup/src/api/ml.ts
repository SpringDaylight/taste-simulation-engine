/**
 * ML API - 취향 분석 및 추천 시스템
 */
import { post } from './http';

// ============================================================
// Types
// ============================================================

export interface EmotionScores {
  [key: string]: number;
}

export interface EndingPreference {
  happy: number;
  open: number;
  bittersweet: number;
}

// A-1: 사용자 취향 분석
export interface AnalyzePreferenceRequest {
  text: string;
  dislikes?: string;
}

export interface UserProfile {
  user_text: string;
  emotion_scores: EmotionScores;
  narrative_traits: EmotionScores;
  direction_mood: EmotionScores;
  character_relationship: EmotionScores;
  ending_preference: EndingPreference;
  dislike_tags: string[];
  boost_tags: string[];
}

// A-2: 영화 벡터화
export interface MovieVectorRequest {
  movie_id: number;
  title: string;
  overview?: string;
  genres?: string[];
  keywords?: string[];
}

export interface MovieProfile {
  movie_id: number;
  title: string;
  emotion_scores: EmotionScores;
  narrative_traits: EmotionScores;
  direction_mood: EmotionScores;
  character_relationship: EmotionScores;
  ending_preference: EndingPreference;
  embedding_text: string;
  embedding: number[];
}

// A-3: 만족 확률 계산
export interface PredictSatisfactionRequest {
  user_id?: string;  // ✅ 문자열 UUID (있으면 백엔드에서 DB 조회)
  user_profile: UserProfile;
  movie_profile: MovieProfile;
  dislike_tags?: string[];
  boost_tags?: string[];
}

export interface PredictionBreakdown {
  emotion_similarity: number;
  narrative_similarity: number;
  direction_similarity: number;
  character_similarity: number;
  ending_similarity: number;
  boost_score: number;
  dislike_penalty: number;
  top_factors: string[];
}

export interface SatisfactionPrediction {
  movie_id: number;
  title: string;
  probability: number;
  confidence: number;
  raw_score: number;
  match_rate: number;
  breakdown: PredictionBreakdown;
}

// A-4: 설명 생성
export interface ExplainPredictionRequest {
  movie_title: string;
  match_rate: number;
  probability: number;
  breakdown: PredictionBreakdown;
  user_liked_tags?: string[];
  user_disliked_tags?: string[];
}

export interface KeyFactor {
  category: string;
  label: string;
  score: number;
}

export interface PredictionExplanation {
  movie_title: string;
  match_rate: number;
  explanation: string;
  key_factors: KeyFactor[];
  disclaimer: string;
}

// A-5: 감성 검색
export interface EmotionalSearchRequest {
  text: string;
  genres?: string[];
  year_from?: number;
  year_to?: number;
}

export interface EmotionalSearchResponse {
  intent: string;
  expanded_query: {
    emotion_scores: EmotionScores;
  };
  hybrid_query: any;
}

// A-6: 그룹 추천
export interface GroupMember {
  user_id: string;
  profile: UserProfile;
  dislikes?: string[];
  likes?: string[];
}

export interface GroupSimulateRequest {
  members: GroupMember[];
  movie_profile: MovieProfile;
  strategy?: 'least_misery' | 'average';
}

export interface MemberSatisfaction {
  user_id: string;
  probability: number;
  confidence: number;
  level: string;
}

export interface GroupStatistics {
  min_satisfaction: number;
  max_satisfaction: number;
  avg_satisfaction: number;
  variance: number;
}

export interface GroupSimulationResult {
  group_score: number;
  strategy: string;
  members: MemberSatisfaction[];
  comment: string;
  recommendation: string;
  statistics: GroupStatistics;
}

// A-7: 취향 지도
export interface TasteMapRequest {
  user_text: string;
  k?: number;
}

export interface ClusterInfo {
  cluster_id: number;
  label: string;
  count: number;
}

export interface UserLocation {
  x: number;
  y: number;
  nearest_cluster: number;
  cluster_label: string;
}

export interface TasteMapResponse {
  clusters: ClusterInfo[];
  user_location: UserLocation;
}

// ============================================================
// API Functions
// ============================================================

/**
 * A-1: 사용자 취향 분석
 * 텍스트 입력으로부터 사용자의 영화 취향을 분석합니다.
 */
export function analyzePreference(data: AnalyzePreferenceRequest): Promise<UserProfile> {
  return post<UserProfile>('/analyze/preference', data);
}

/**
 * A-2: 영화 벡터화
 * 영화 메타데이터를 특성 벡터로 변환합니다.
 */
export function vectorizeMovie(data: MovieVectorRequest): Promise<MovieProfile> {
  return post<MovieProfile>('/movie/vector', data);
}

/**
 * A-3: 만족 확률 계산
 * 사용자 프로필과 영화 프로필을 비교하여 만족 확률을 계산합니다.
 */
export function predictSatisfaction(data: PredictSatisfactionRequest): Promise<SatisfactionPrediction> {
  return post<SatisfactionPrediction>('/predict/satisfaction', data);
}

/**
 * A-4: 설명 생성
 * 예측 결과에 대한 자연어 설명을 생성합니다.
 */
export function explainPrediction(data: ExplainPredictionRequest): Promise<PredictionExplanation> {
  return post<PredictionExplanation>('/explain/prediction', data);
}

/**
 * A-5: 감성 검색
 * 자연어 쿼리로 영화를 감성 기반 검색합니다.
 */
export function emotionalSearch(data: EmotionalSearchRequest): Promise<EmotionalSearchResponse> {
  return post<EmotionalSearchResponse>('/search/emotional', data);
}

/**
 * A-6: 그룹 추천
 * 여러 사용자의 취향을 종합하여 그룹 만족도를 계산합니다.
 */
export function simulateGroup(data: GroupSimulateRequest): Promise<GroupSimulationResult> {
  return post<GroupSimulationResult>('/group/simulate', data);
}

/**
 * A-7: 취향 지도
 * 사용자의 취향을 시각화할 수 있는 클러스터 정보를 제공합니다.
 */
export function getTasteMap(data: TasteMapRequest): Promise<TasteMapResponse> {
  return post<TasteMapResponse>('/map/taste', data);
}

// ============================================================
// Helper Functions
// ============================================================

/**
 * 영화 추천 전체 플로우
 * 사용자 입력 → 취향 분석 → 영화 벡터화 → 만족 확률 계산 → 설명 생성
 */
export async function getMovieRecommendation(
  userText: string,
  userDislikes: string | undefined,
  movieData: MovieVectorRequest
): Promise<{
  userProfile: UserProfile;
  movieProfile: MovieProfile;
  prediction: SatisfactionPrediction;
  explanation: PredictionExplanation;
}> {
  // 1. 사용자 취향 분석
  const userProfile = await analyzePreference({
    text: userText,
    dislikes: userDislikes,
  });

  // 2. 영화 벡터화
  const movieProfile = await vectorizeMovie(movieData);

  // 3. 만족 확률 계산
  const prediction = await predictSatisfaction({
    user_profile: userProfile,
    movie_profile: movieProfile,
    dislike_tags: userProfile.dislike_tags,
    boost_tags: userProfile.boost_tags,
  });

  // 4. 설명 생성
  const explanation = await explainPrediction({
    movie_title: movieData.title,
    match_rate: prediction.match_rate,
    probability: prediction.probability,
    breakdown: prediction.breakdown,
    user_liked_tags: userProfile.boost_tags,
    user_disliked_tags: userProfile.dislike_tags,
  });

  return {
    userProfile,
    movieProfile,
    prediction,
    explanation,
  };
}
