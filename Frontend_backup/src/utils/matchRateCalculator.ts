/**
 * 영화 적합도 계산 유틸리티
 * HomePage와 MovieDetailPage에서 동일한 로직 사용
 */
import { checkUserPreferenceExists, getUserPreference } from "../api/userPreferences";
import type { Movie } from "../api/A2_movies";
import type { SatisfactionPrediction } from "../api/ml";
import { getAccessToken } from "../api/http";
import { getCurrentUser } from "../api/A7_profile";

const CACHE_KEY_PREFIX = "mw_match_rate_cache_";

/**
 * 캐시 키 생성
 */
const getCacheKey = (movieId: number, userTasteText: string): string => {
  // 사용자 취향 텍스트의 해시를 포함하여 취향이 바뀌면 캐시 무효화
  const hash = userTasteText.substring(0, 50);
  return `${CACHE_KEY_PREFIX}${movieId}_${hash}`;
};

/**
 * 캐시에 저장
 */
const saveToCache = (cacheKey: string, data: SatisfactionPrediction): void => {
  try {
    sessionStorage.setItem(cacheKey, JSON.stringify({
      data,
      timestamp: Date.now()
    }));
  } catch (error) {
    console.warn("Failed to save to cache:", error);
  }
};

/**
 * 사용자 취향 정보 가져오기
 * - 로그인 사용자: DB에서만 조회 (없으면 에러)
 * - 비로그인 사용자: localStorage 사용
 */
export const getUserTasteData = async () => {
  // user_preferences.user_id는 users.id를 참조하므로 mw_user_pk 사용
  const isLoggedIn = Boolean(getAccessToken());
  let userPk: string | null = null;
  if (isLoggedIn) {
    try {
      const currentUser = await getCurrentUser();
      userPk = currentUser.id;
    } catch (error) {
      console.warn("Failed to load current user for taste data:", error);
      userPk = null;
    }
  }
  
  // 로그인한 사용자는 반드시 DB에서 가져와야 함
  if (isLoggedIn && userPk) {
    const exists = await checkUserPreferenceExists(userPk);
    if (!exists.exists) {
      throw new Error("User preference not found");
    }
    const preference = await getUserPreference(userPk);
    
    // DB에서 가져온 데이터를 변환
    const topEmotions = Object.entries(preference.preference_vector_json.emotion_scores)
      .sort(([_, a], [__, b]) => b - a)
      .slice(0, 3)
      .map(([tag, _]) => tag);
    
    const topNarratives = Object.entries(preference.preference_vector_json.narrative_traits)
      .sort(([_, a], [__, b]) => b - a)
      .slice(0, 3)
      .map(([tag, _]) => tag);
    
    return {
      userTasteText: topEmotions.join(", "),
      userKeywords: topNarratives,
      userAvoidGenres: preference.penalty_tags || [],
      userProfile: preference.preference_vector_json,
      fromDatabase: true,
    };
  }
  
  // 비로그인 사용자는 localStorage 사용
  const userTasteText = localStorage.getItem("mw_taste_vibe") || "";
  const userKeywords = (() => {
    try {
      const parsed = JSON.parse(localStorage.getItem("mw_taste_keywords") || "[]");
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return [];
    }
  })();
  const userAvoidGenres = (() => {
    try {
      const parsed = JSON.parse(localStorage.getItem("mw_taste_avoid_genres") || "[]");
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return [];
    }
  })();
  
  const userProfileStr = localStorage.getItem("mw_user_profile");
  const userProfile = userProfileStr ? JSON.parse(userProfileStr) : null;

  return {
    userTasteText,
    userKeywords,
    userAvoidGenres,
    userProfile,
    fromDatabase: false,
  };
};

/**
 * 단일 영화의 적합도 계산 (캐싱 포함)
 */
export const calculateMovieMatchRate = async (
  movie: Movie
): Promise<SatisfactionPrediction | null> => {
  const tasteData = await getUserTasteData();
  const { userTasteText, userProfile } = tasteData;

  if (!userTasteText.trim() && !userProfile) {
    return null;
  }

  const fullUserText = `${userTasteText}`.trim();
  const cacheKey = getCacheKey(movie.id, fullUserText);
  
  // 캐시 확인 (임시로 비활성화)
  // const cached = getFromCache(cacheKey);
  // if (cached) {
  //   console.log(`Cache hit for movie ${movie.id}`);
  //   return cached;
  // }

  console.log(`🔄 Cache disabled, calculating for movie ${movie.id}...`);

  // 로그인 확인 (JWT 토큰만 확인)
  const accessToken = localStorage.getItem("mw_access_token");
  
  console.log('🔍 [MatchRate] 로그인 상태 확인:', {
    hasAccessToken: !!accessToken
  });
  
  if (!accessToken) {
    console.log('⚠️ [MatchRate] 로그인 안 됨, 만족도 계산 불가');
    return null;
  }

  // /api/llm/satisfaction 직접 호출 (JWT 인증)
  console.log('🔍 [MatchRate] Calling /api/llm/satisfaction with JWT');
  
  try {
    const { calculateSatisfaction } = await import('../api/llmRecommend');
    
    // JWT 인증을 사용하므로 user_id 전달 불필요
    const response = await calculateSatisfaction({
      movie_id: movie.id
    });
    
    // SatisfactionPrediction 형식으로 변환
    const prediction: SatisfactionPrediction = {
      movie_id: movie.id,
      title: movie.title,
      probability: response.satisfaction_probability,
      confidence: response.confidence || 0,
      raw_score: 0, // breakdown에서 계산 가능
      match_rate: response.satisfaction_probability * 100,
      breakdown: {
        emotion_similarity: response.breakdown?.emotion_similarity || 0,
        narrative_similarity: response.breakdown?.narrative_similarity || 0,
        direction_similarity: 0, // Not provided by /api/llm/satisfaction
        character_similarity: 0, // Not provided by /api/llm/satisfaction
        ending_similarity: response.breakdown?.ending_similarity || 0,
        boost_score: response.breakdown?.boost_score || 0,
        dislike_penalty: response.breakdown?.dislike_penalty || 0,
        top_factors: response.breakdown?.top_factors || []
      }
    };
    
    console.log('✅ [MatchRate] /api/llm/satisfaction result:', {
      probability: prediction.probability,
      match_rate: prediction.match_rate
    });
    
    // 캐시에 저장
    saveToCache(cacheKey, prediction);
    
    return prediction;
  } catch (error) {
    console.error('❌ [MatchRate] Error:', error);
    return null;
  }
};

/**
 * 여러 영화의 적합도 계산 (배치)
 */
export const calculateMoviesMatchRates = async (
  movies: Movie[]
): Promise<Record<number, number>> => {
  if (movies.length === 0) {
    return {};
  }

  const tasteData = await getUserTasteData();
  const { userTasteText, userProfile } = tasteData;
  
  if (!userTasteText.trim() && !userProfile) {
    return {};
  }

  const results = await Promise.all(
    movies.map(async (movie) => {
      const result = await calculateMovieMatchRate(movie);
      return [movie.id, result ? Math.round(result.match_rate) : 83] as const;
    })
  );

  return Object.fromEntries(results);
};
