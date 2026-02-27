/**
 * 사용자 선호도 동기화 유틸리티
 * 백엔드 UserPreference와 프론트엔드 localStorage 동기화
 */
import { 
  getUserPreference, 
  saveUserPreference,
  type UserPreference,
  type SaveUserPreferenceRequest 
} from "../api/userPreferences";
import { analyzePreference } from "../api/ml";

/**
 * 백엔드에서 최신 사용자 선호도 가져오기
 */
export const fetchUserPreference = async (userId: string): Promise<UserPreference | null> => {
  try {
    const response = await getUserPreference(userId);
    return response;
  } catch (error) {
    console.error("Failed to fetch user preference:", error);
    return null;
  }
};

/**
 * 백엔드 선호도를 localStorage에 동기화
 */
export const syncUserPreferenceToLocal = async (userId: string): Promise<boolean> => {
  try {
    const preference = await fetchUserPreference(userId);
    
    if (!preference) {
      return false;
    }

    // localStorage에 저장 (기존 키 유지)
    const { preference_vector_json, penalty_tags } = preference;
    
    // 감정 태그를 텍스트로 변환 (상위 3개)
    const topEmotions = Object.entries(preference_vector_json.emotion_scores)
      .sort(([_, a], [__, b]) => b - a)
      .slice(0, 3)
      .map(([tag, _]) => tag);
    
    const topNarratives = Object.entries(preference_vector_json.narrative_traits)
      .sort(([_, a], [__, b]) => b - a)
      .slice(0, 3)
      .map(([tag, _]) => tag);
    
    // mw_taste_vibe: 주요 감정 태그
    localStorage.setItem("mw_taste_vibe", topEmotions.join(", "));
    
    // mw_taste_keywords: 서사 특성 태그
    localStorage.setItem("mw_taste_keywords", JSON.stringify(topNarratives));
    
    // mw_taste_avoid_genres: 싫어하는 태그
    localStorage.setItem("mw_taste_avoid_genres", JSON.stringify(penalty_tags));
    
    // 전체 프로필 저장
    localStorage.setItem("mw_user_profile", JSON.stringify(preference_vector_json));
    
    console.log("User preference synced to localStorage");
    return true;
  } catch (error) {
    console.error("Failed to sync user preference:", error);
    return false;
  }
};

/**
 * localStorage의 취향 데이터를 백엔드에 저장
 */
export const saveLocalPreferenceToBackend = async (userId: string): Promise<boolean> => {
  try {
    const userTasteText = localStorage.getItem("mw_taste_vibe") || "";
    const userKeywords = JSON.parse(localStorage.getItem("mw_taste_keywords") || "[]");
    const userAvoidGenres = JSON.parse(localStorage.getItem("mw_taste_avoid_genres") || "[]");
    
    if (!userTasteText.trim()) {
      console.warn("No taste data to save");
      return false;
    }
    
    // 취향 분석
    const fullUserText = `${userTasteText} ${userKeywords.join(", ")}`.trim();
    const userProfile = await analyzePreference({
      text: fullUserText,
      dislikes: userAvoidGenres.length ? userAvoidGenres.join(", ") : undefined,
    });
    
    // 백엔드에 저장
    const request: SaveUserPreferenceRequest = {
      user_id: userId,
      preference_vector_json: {
        emotion_scores: userProfile.emotion_scores,
        narrative_traits: userProfile.narrative_traits,
        direction_mood: userProfile.direction_mood,
        character_relationship: userProfile.character_relationship,
        ending_preference: userProfile.ending_preference,
      },
      boost_tags: userProfile.boost_tags,
      dislike_tags: userProfile.dislike_tags,
      penalty_tags: [],
    };
    
    await saveUserPreference(request);
    console.log("Local preference saved to backend");
    return true;
  } catch (error) {
    console.error("Failed to save local preference to backend:", error);
    return false;
  }
};

/**
 * 리뷰 작성 후 선호도 동기화 및 캐시 무효화
 */
export const syncAfterReview = async (userId: string): Promise<void> => {
  try {
    // 백엔드 최신 선호도는 캐시 갱신 용도로만 조회
    await fetchUserPreference(userId);
  } catch {
    // ignore fetch errors; cache invalidation still proceeds
  }

  // 적합도 캐시 무효화
  clearMatchRateCache();
};

/**
 * 적합도 캐시 전체 무효화
 */
export const clearMatchRateCache = (): void => {
  try {
    const keys = Object.keys(sessionStorage);
    const cacheKeys = keys.filter(key => key.startsWith("mw_match_rate_cache_"));
    
    cacheKeys.forEach(key => {
      sessionStorage.removeItem(key);
    });
    
    console.log(`Cleared ${cacheKeys.length} match rate cache entries`);
  } catch (error) {
    console.error("Failed to clear match rate cache:", error);
  }
};
