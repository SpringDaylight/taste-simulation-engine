/**
 * 취향 설문 모달 컴포넌트
 * 로그인 필수 - DB에 직접 저장
 */
import { useState, type Dispatch, type SetStateAction } from "react";
import { analyzePreference } from "../api/ml";
import { processGenreTags } from "../utils/tagProcessor";
import { getCurrentUser } from "../api/A7_profile";
import { getAccessToken } from "../api/http";

const genreLikeOptions = [
  "💕 로맨스 / 로코",
  "😂 코미디",
  "😢 드라마 / 휴먼",
  "🔪 스릴러 / 미스터리",
  "👻 공포 / 호러",
  "👊 액션",
  "🚔 범죄 / 느와르",
  "👽 SF",
  "🧙 판타지",
  "🧚 애니메이션",
  "⚔️ 전쟁 / 역사",
  "🎥 다큐멘터리",
];

const avoidNoneLabel = "선택 없음 (중복 불가!)";
const avoidNoneAliases = [
  avoidNoneLabel,
  "선택 없음 (중복불가!)",
  "선택 없음",
];

const genreAvoidOptions = [
  "💕 로맨스 / 로코",
  "😂 코미디",
  "😢 드라마 / 휴먼",
  "🔪 스릴러 / 미스터리",
  "👻 공포 / 호러",
  "👊 액션",
  "🚔 범죄 / 느와르",
  "👽 SF",
  "🧙 판타지",
  "🧚 애니메이션",
  "⚔️ 전쟁 / 역사",
  "🎥 다큐멘터리",
  avoidNoneLabel,
];

const contextOptions = [
  "🧘 혼자 몰입파",
  "💑 연인/친구와 함께",
  "👨👩👧👦 가족과 오순도순",
  "🌙 자기 전 가볍게",
  "🍿 주말에 각 잡고 진득하게",
];

const vibeOptions = [
  "😀 가볍고 유쾌한",
  "🥲 감동적이고 따뜻한",
  "🤯 충격적이고 강렬한",
  "🌿 여유롭고 잔잔한",
  "🤔 철학적이고 생각하게 만드는",
  "😰 긴장감 있는",
];

const keywordOptions = [
  "✨ 성장 / 청춘",
  "🤝 가족 / 우정",
  "💼 전문직 / 직업물",
  "📜 실화 기반",
  "🧟 디스토피아 / 아포칼립스",
  "🔄 타임루프 / 시간여행",
  "🎮 게임 / 가상세계",
  "🔎 본격 추리",
  "🎵 음악 / 예술",
  "⚽ 스포츠",
];

const originOptions = [
  "🇰🇷 한국 영화",
  "🇺🇸 미국/할리우드",
  "🇯🇵 일본 영화/애니",
  "🌍 유럽/기타 해외",
  "🎞 고전 명작",
];

const totalSurveySteps = 6;

interface TasteSurveyModalProps {
  onClose: () => void;
  onComplete: () => void;
  initialData?: {
    favorite_genres?: string[];
    disliked_genres?: string[];
    viewing_context?: string;
    preferred_vibe?: string;
    interest_keywords?: string[];
    preferred_origin?: string;
  };
}

const normalizeKey = (value: string) => value.replace(/\s+/g, "").trim();
const isAvoidNone = (value: string) =>
  avoidNoneAliases.some((label) => normalizeKey(label) === normalizeKey(value));

// 장르 옵션에서 이모지 제거하여 매칭
const removeEmoji = (text: string) => text.replace(/^[^\w\s가-힣/]+\s*/, "").trim();

// / 구분자로 된 문자열을 배열로 분리
const splitKeywords = (keywordString: string): string[] => 
  keywordString.split("/").map(k => k.trim()).filter(k => k.length > 0);

// DB에 저장된 장르 배열을 UI 옵션과 매칭
// DB: ["로맨스", "로코"] -> UI: "💕 로맨스 / 로코"
const mapGenresToOptions = (dbGenres: string[]): string[] => {
  const result: string[] = [];
  const used = new Set<number>();
  
  // 각 UI 옵션에 대해
  for (const option of genreLikeOptions) {
    const optionParts = processGenreTags([option]); // ["로맨스", "로코"]
    
    // DB 장르 중에서 이 옵션의 모든 부분이 연속으로 있는지 확인
    let allFound = true;
    const indices: number[] = [];
    
    for (const part of optionParts) {
      const idx = dbGenres.findIndex((g, i) => !used.has(i) && g === part);
      if (idx === -1) {
        allFound = false;
        break;
      }
      indices.push(idx);
    }
    
    if (allFound && indices.length > 0) {
      // 연속된 인덱스인지 확인
      const sorted = [...indices].sort((a, b) => a - b);
      let isConsecutive = true;
      for (let i = 1; i < sorted.length; i++) {
        if (sorted[i] !== sorted[i-1] + 1) {
          isConsecutive = false;
          break;
        }
      }
      
      if (isConsecutive) {
        result.push(option);
        indices.forEach(i => used.add(i));
      }
    }
  }
  
  // 매칭되지 않은 장르들은 개별적으로 추가
  dbGenres.forEach((genre, idx) => {
    if (!used.has(idx)) {
      result.push(genre);
    }
  });
  
  return result;
};

const mapContextToOption = (context: string): string => {
  const normalized = removeEmoji(context);
  const option = contextOptions.find(opt => removeEmoji(opt) === normalized);
  return option || context;
};

const mapVibeToOption = (vibe: string): string => {
  const normalized = removeEmoji(vibe);
  const option = vibeOptions.find(opt => removeEmoji(opt) === normalized);
  return option || vibe;
};

const mapKeywordToOption = (keyword: string): string => {
  const normalized = removeEmoji(keyword);
  const option = keywordOptions.find(opt => removeEmoji(opt) === normalized);
  return option || keyword;
};

const mapOriginToOption = (origin: string): string => {
  const normalized = removeEmoji(origin);
  const option = originOptions.find(opt => removeEmoji(opt) === normalized);
  return option || origin;
};

export default function TasteSurveyModal({ onClose, onComplete, initialData }: TasteSurveyModalProps) {
  const [surveyStep, setSurveyStep] = useState(0);
  const [genres, setGenres] = useState<string[]>(() => 
    initialData?.favorite_genres ? mapGenresToOptions(initialData.favorite_genres) : []
  );
  const [avoidGenres, setAvoidGenres] = useState<string[]>(() => 
    initialData?.disliked_genres ? mapGenresToOptions(initialData.disliked_genres) : []
  );
  const [context, setContext] = useState(() => 
    initialData?.viewing_context ? mapContextToOption(initialData.viewing_context) : ""
  );
  const [vibe, setVibe] = useState<string[]>(() => {
    if (!initialData?.preferred_vibe) return [];
    // / 구분자로 분리된 경우 처리
    const vibes = initialData.preferred_vibe.includes("/") 
      ? splitKeywords(initialData.preferred_vibe)
      : [initialData.preferred_vibe];
    return vibes.map(mapVibeToOption);
  });
  const [keywords, setKeywords] = useState<string[]>(() => {
    if (!initialData?.interest_keywords || initialData.interest_keywords.length === 0) {
      console.log('Keywords initialized: empty array');
      return [];
    }
    // 장르처럼 배열로 저장된 경우 각각 매칭
    const result = initialData.interest_keywords.map(mapKeywordToOption);
    console.log('Keywords initialized from array:', result);
    return result;
  });
  const [origin, setOrigin] = useState(() => 
    initialData?.preferred_origin ? mapOriginToOption(initialData.preferred_origin) : ""
  );
  const [submitting, setSubmitting] = useState(false);

  const toggleValueWithLimit = (
    value: string,
    setList: Dispatch<SetStateAction<string[]>>,
    limit: number
  ) => {
    console.log('toggleValueWithLimit called:', { value, limit });
    setList((prev) => {
      console.log('Previous state:', prev);
      if (prev.includes(value)) {
        const newState = prev.filter((item) => item !== value);
        console.log('Removing, new state:', newState);
        return newState;
      }
      if (prev.length >= limit) {
        console.log('Limit reached, not adding');
        return prev;
      }
      const newState = [...prev, value];
      console.log('Adding, new state:', newState);
      return newState;
    });
  };

  const toggleGenre = (value: string) => {
    setGenres((prev) => {
      if (prev.includes(value)) {
        return prev.filter((item) => item !== value);
      }
      if (prev.length >= 5) {
        return prev;
      }
      // 싫어하는 장르에 있으면 제거
      if (avoidGenres.includes(value)) {
        setAvoidGenres((avoid) => avoid.filter((item) => item !== value));
      }
      return [...prev, value];
    });
  };

  const toggleSingleValue = (
    value: string,
    setValue: Dispatch<SetStateAction<string>>
  ) => {
    setValue((prev) => (prev === value ? "" : value));
  };

  const toggleAvoidGenre = (value: string) => {
    setAvoidGenres((prev) => {
      if (value === avoidNoneLabel) {
        return prev.some(isAvoidNone) ? [] : [avoidNoneLabel];
      }
      const withoutNone = prev.filter((item) => !isAvoidNone(item));
      if (withoutNone.includes(value)) {
        return withoutNone.filter((item) => item !== value);
      }
      // 최대 3개 제한
      if (withoutNone.length >= 3) {
        return withoutNone;
      }
      // 좋아하는 장르에 있으면 제거
      if (genres.includes(value)) {
        setGenres((liked) => liked.filter((item) => item !== value));
      }
      return [...withoutNone, value];
    });
  };

  const handleNext = () => {
    if (surveyStep < totalSurveySteps) {
      setSurveyStep(surveyStep + 1);
    }
  };

  const handlePrev = () => {
    if (surveyStep > 0) {
      setSurveyStep(surveyStep - 1);
    }
  };

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      // 로그인 체크
      const isLoggedIn = Boolean(getAccessToken());
      if (!isLoggedIn) {
        alert("로그인이 필요합니다.");
        onClose();
        return;
      }

      // 최소 선택 검증
      if (genres.length === 0) {
        alert("좋아하는 장르를 최소 1개 이상 선택해주세요.");
        setSubmitting(false);
        return;
      }

      // 장르 정리: 이모지 제거 후 '/' 분리
      const processedGenres = processGenreTags(genres);
      const processedAvoidGenres = processGenreTags(
        avoidGenres.filter((g) => !isAvoidNone(g))
      );

      // 이모지 제거
      const cleanedContext = removeEmoji(context);
      const cleanedVibes = vibe.map(removeEmoji);
      const cleanedKeywords = keywords.map(removeEmoji);
      const cleanedOrigin = removeEmoji(origin);

      // ML API: 취향 분석 수행
      const userText = `${vibe.join(", ")} ${keywords.join(", ")} ${processedGenres.join(", ")}`;
      const userDislikes = processedAvoidGenres.join(", ");

      const userProfile = await analyzePreference({
        text: userText,
        dislikes: userDislikes || undefined,
      });

      // DB에 저장
      const { saveUserPreference } = await import("../api/userPreferences");
      const currentUser = await getCurrentUser();

      await saveUserPreference({
        user_id: currentUser.id,
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
        
        // Survey fields 추가
        favorite_genres: processedGenres, // ["로맨스", "로코", "코미디"]
        disliked_genres: processedAvoidGenres,
        viewing_context: cleanedContext,
        preferred_vibe: cleanedVibes.join(" / "), // 복수 선택 가능하므로 / 구분자로 결합
        interest_keywords: cleanedKeywords, // ["성장 / 청춘", "디스토피아 / 아포칼립스", "타임루프 / 시간여행"]
        preferred_origin: cleanedOrigin,
      });

      onComplete();
    } catch (err) {
      console.error("Failed to analyze preference:", err);
      alert("취향 분석 중 오류가 발생했습니다.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="modal" role="dialog" aria-modal="true">
      <div className="modal-overlay" onClick={onClose} />
      <div className="modal-content">
        <div className="modal-scroll">
          <div className="modal-header">
            {surveyStep === 0 ? (
              <h2>취향 분석 설문</h2>
            ) : (
              <h2>
                취향 분석 설문 {surveyStep}/{totalSurveySteps}
              </h2>
            )}
            <button className="icon-btn" type="button" aria-label="닫기" onClick={onClose}>
              ×
            </button>
          </div>

          <div className="modal-section">
            {surveyStep === 0 && (
              <p className="muted">
                당신에게 맞는 영화를 추천하기 위해 간단한 질문을 드릴게요.
              </p>
            )}

            {surveyStep === 1 && (
              <>
                <h3 className="filter-title">가장 좋아하는 장르를 골라주세요 (최소 1개, 최대 5개)</h3>
                <div className="tag-list">
                  {genreLikeOptions.map((genre) => (
                    <button
                      key={genre}
                      className={`filter-chip ${genres.includes(genre) ? "active" : ""}`}
                      type="button"
                      onClick={() => toggleGenre(genre)}
                    >
                      {genre}
                    </button>
                  ))}
                </div>
              </>
            )}

            {surveyStep === 2 && (
              <>
                <h3 className="filter-title">아쉽지만 선호하지 않는 장르도 알려주세요 (최대 3개, 선택)</h3>
                <div className="tag-list">
                  {genreAvoidOptions.map((genre) => (
                    <button
                      key={`avoid-${genre}`}
                      className={`filter-chip ${avoidGenres.includes(genre) ? "active" : ""}`}
                      type="button"
                      onClick={() => toggleAvoidGenre(genre)}
                    >
                      {genre}
                    </button>
                  ))}
                </div>
              </>
            )}

            {surveyStep === 3 && (
              <>
                <h3 className="filter-title">보통 영화를 언제, 어떻게 즐기시나요? (1개 선택)</h3>
                <div className="tag-list">
                  {contextOptions.map((option) => (
                    <button
                      key={option}
                      className={`filter-chip ${context === option ? "active" : ""}`}
                      type="button"
                      onClick={() => toggleSingleValue(option, setContext)}
                    >
                      {option}
                    </button>
                  ))}
                </div>
              </>
            )}

            {surveyStep === 4 && (
              <>
                <h3 className="filter-title">어떤 분위기의 영화가 끌리시나요? (최대 2개)</h3>
                <div className="tag-list">
                  {vibeOptions.map((option) => (
                    <button
                      key={option}
                      className={`filter-chip ${vibe.includes(option) ? "active" : ""}`}
                      type="button"
                      onClick={() => toggleValueWithLimit(option, setVibe, 2)}
                    >
                      {option}
                    </button>
                  ))}
                </div>
              </>
            )}

            {surveyStep === 5 && (
              <>
                <h3 className="filter-title">관심 있는 키워드를 골라주세요 (최대 3개)</h3>
                <div className="tag-list">
                  {keywordOptions.map((option) => (
                    <button
                      key={option}
                      className={`filter-chip ${keywords.includes(option) ? "active" : ""}`}
                      type="button"
                      onClick={() => toggleValueWithLimit(option, setKeywords, 3)}
                    >
                      {option}
                    </button>
                  ))}
                </div>
              </>
            )}

            {surveyStep === 6 && (
              <>
                <h3 className="filter-title">주로 어디 나라 영화를 보시나요? (1개 선택)</h3>
                <div className="tag-list">
                  {originOptions.map((option) => (
                    <button
                      key={option}
                      className={`filter-chip ${origin === option ? "active" : ""}`}
                      type="button"
                      onClick={() => toggleSingleValue(option, setOrigin)}
                    >
                      {option}
                    </button>
                  ))}
                </div>
              </>
            )}
          </div>

          <div className="modal-footer">
            {surveyStep === 0 && (
              <button
                className="secondary-btn survey-nav-btn"
                type="button"
                onClick={handleNext}
              >
                시작하기
              </button>
            )}
            {surveyStep > 0 && surveyStep < totalSurveySteps && (
              <>
                <button
                  className="secondary-btn survey-nav-btn"
                  type="button"
                  onClick={handlePrev}
                >
                  이전
                </button>
                <button
                  className="secondary-btn survey-nav-btn"
                  type="button"
                  onClick={handleNext}
                >
                  다음
                </button>
              </>
            )}
            {surveyStep === totalSurveySteps && (
              <>
                <button
                  className="secondary-btn survey-nav-btn"
                  type="button"
                  onClick={handlePrev}
                >
                  이전
                </button>
                <button
                  className="secondary-btn survey-nav-btn"
                  type="button"
                  onClick={handleSubmit}
                  disabled={submitting}
                >
                  {submitting ? "저장 중..." : "완료"}
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
