import { useState, useEffect, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { recommendMovies, explainRecommendation, type Movie } from '../api/llmRecommend';
import MainLayout from '../components/layout/MainLayout';
import '../styles/LLMRecommendPage.css';
import {
  getStorageItem,
  removeStorageItem,
  setJsonToStorage,
  safeParseJson,
} from '../utils/storage';
import { getCurrentUser } from '../api/users';
import { getAccessToken } from '../api/http';

// localStorage 상태 저장
const STORAGE_KEY = 'llm_recommend_state';

// 저장할 상태 타입
interface SavedState {
  input: string;
  recommendations: Movie[];
  explanation: string;
  useOrchestrator: boolean;
  keywordCandidates: Movie[];
  vectorCandidates: Movie[];
  keywordWeight: number;
  emotionWeight: number;
  timestamp: number;
  userId?: string;  // 사용자 ID 추가
}

export default function LLMRecommendPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const lastAutoQueryRef = useRef<string | null>(null);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isLoggedIn, setIsLoggedIn] = useState(() => Boolean(getAccessToken()));
  const [recommendations, setRecommendations] = useState<Movie[]>([]);
  const [explanation, setExplanation] = useState('');
  const [error, setError] = useState('');
  const [inlineWarning, setInlineWarning] = useState<string | null>(null);
  const [warningTick, setWarningTick] = useState(0);
  const useOrchestrator = true;  // 항상 오케스트레이터 모드 사용
  const [keywordCandidates, setKeywordCandidates] = useState<Movie[]>([]);
  const [vectorCandidates, setVectorCandidates] = useState<Movie[]>([]);
  const [keywordWeight, setKeywordWeight] = useState<number>(0);
  const [emotionWeight, setEmotionWeight] = useState<number>(0);
  const [expandedExplanations, setExpandedExplanations] = useState<Record<number, string>>({});
  const [loadingExplanations, setLoadingExplanations] = useState<Record<number, boolean>>({});
  const [visibleExplanations, setVisibleExplanations] = useState<Record<number, boolean>>({});

  // 컴포넌트 마운트 시 localStorage에서 복원
  useEffect(() => {
    const syncAuthState = () => {
      setIsLoggedIn(Boolean(getAccessToken()));
    };

    syncAuthState();

    const handleAuthChange = () => syncAuthState();
    window.addEventListener("mw_auth_change", handleAuthChange);
    window.addEventListener("storage", handleAuthChange);

    const restoreState = async () => {
      try {
        const saved = getStorageItem(STORAGE_KEY);
        if (!saved) return;

        const state = safeParseJson<SavedState | null>(saved, null);
        if (!state) {
          removeStorageItem(STORAGE_KEY);
          return;
        }

        // 로그인 상태 확인
        const isLoggedIn = Boolean(getAccessToken());
        
        // 로그인 상태라면 현재 사용자 확인
        if (isLoggedIn) {
          try {
            const currentUser = await getCurrentUser();
            const currentUserId = currentUser.user_id || currentUser.id;
            
            // 저장된 userId와 현재 userId가 다르면 캐시 삭제
            if (state.userId && state.userId !== currentUserId) {
              console.log('User changed, clearing LLM recommendation cache');
              removeStorageItem(STORAGE_KEY);
              return;
            }
          } catch (err) {
            // 사용자 정보를 가져올 수 없으면 (세션 만료 등) 캐시 삭제
            console.log('Failed to get current user, clearing cache');
            removeStorageItem(STORAGE_KEY);
            return;
          }
        } else {
          // 로그아웃 상태인데 userId가 저장되어 있으면 캐시 삭제
          if (state.userId) {
            console.log('User logged out, clearing LLM recommendation cache');
            removeStorageItem(STORAGE_KEY);
            return;
          }
        }
        
        // 24시간 이내 데이터만 복원
        const ONE_DAY = 24 * 60 * 60 * 1000;
        if (Date.now() - state.timestamp < ONE_DAY) {
          setInput(state.input);
          setRecommendations(state.recommendations);
          setExplanation(state.explanation);
          setKeywordCandidates(state.keywordCandidates || []);
          setVectorCandidates(state.vectorCandidates || []);
          setKeywordWeight(state.keywordWeight || 0);
          setEmotionWeight(state.emotionWeight || 0);
        } else {
          // 오래된 데이터는 삭제
          removeStorageItem(STORAGE_KEY);
        }
      } catch (err) {
        console.error('Failed to restore state:', err);
        removeStorageItem(STORAGE_KEY);
      }
    };

    restoreState();

    return () => {
      window.removeEventListener("mw_auth_change", handleAuthChange);
      window.removeEventListener("storage", handleAuthChange);
    };
  }, []);

  useEffect(() => {
    if (isLoggedIn) {
      setInlineWarning(null);
    }
  }, [isLoggedIn]);

  const showInlineWarning = (message: string) => {
    setInlineWarning(message);
    setWarningTick((prev) => prev + 1);
  };

  // 상태 변경 시 localStorage에 저장
  useEffect(() => {
    // 추천 결과가 있을 때만 저장
    if (recommendations.length > 0) {
      const saveState = async () => {
        try {
          // 현재 사용자 ID 가져오기
          let userId: string | undefined;
          if (getAccessToken()) {
            try {
              const currentUser = await getCurrentUser();
              userId = currentUser.user_id || currentUser.id;
            } catch (err) {
              console.error('Failed to get user for cache:', err);
            }
          }

          const state: SavedState = {
            input,
            recommendations,
            explanation,
            useOrchestrator,
            keywordCandidates,
            vectorCandidates,
            keywordWeight,
            emotionWeight,
            timestamp: Date.now(),
            userId  // 사용자 ID 포함
          };
          setJsonToStorage(STORAGE_KEY, state);
        } catch (err) {
          console.error('Failed to save state:', err);
        }
      };

      saveState();
    }
  }, [input, recommendations, explanation, useOrchestrator, keywordCandidates, vectorCandidates, keywordWeight, emotionWeight]);

  const handleRecommend = async (value?: string) => {
    if (!isLoggedIn) {
      setError('');
      showInlineWarning("로그인 후 이용해주세요.");
      return;
    }
    const query = (value ?? input).trim();
    if (!query || isLoading) return;

    // 새로운 추천 시도 시 이전 캐시 삭제
    removeStorageItem(STORAGE_KEY);

    setIsLoading(true);
    setError('');
    setRecommendations([]);
    setExplanation('');
    setKeywordCandidates([]);
    setVectorCandidates([]);
    setExpandedExplanations({});  // AI 상세 설명 캐시 초기화
    setVisibleExplanations({});  // AI 상세 설명 표시 상태 초기화
    setInput(query);

    try {
      const response = await recommendMovies({
        user_input: query,
        top_k: 5,
        use_orchestrator: useOrchestrator
      });

      setRecommendations(response.recommendations);
      setExplanation(response.explanation);
      setKeywordCandidates(response.keyword_candidates || []);
      setVectorCandidates(response.vector_candidates || []);
      setKeywordWeight(response.keyword_weight || 0);
      setEmotionWeight(response.emotion_weight || 0);
    } catch (err) {
      console.error('Recommendation error:', err);
      setError(err instanceof Error ? err.message : '추천 요청에 실패했습니다.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleClear = () => {
    setInput('');
    setRecommendations([]);
    setExplanation('');
    setError('');
    setKeywordCandidates([]);
    setVectorCandidates([]);
    removeStorageItem(STORAGE_KEY);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleRecommend();
    }
  };

  const handleRecommendClick: React.MouseEventHandler<HTMLButtonElement> = () => {
    handleRecommend();
  };

  const handleMovieClick = (movie: Movie) => {
    navigate(movie.detail_url);
  };

  // 추가 추천 영화 선정 (메인 추천과 겹치지 않게, 가중치 비율로 5개)
  const getAdditionalRecommendations = (): Movie[] => {
    if (!keywordCandidates.length && !vectorCandidates.length) return [];
    
    // 메인 추천 영화 ID 집합
    const mainMovieIds = new Set(recommendations.map(m => m.movie_id));
    
    // 겹치지 않는 후보만 필터링
    const uniqueKeywordCandidates = keywordCandidates.filter(m => !mainMovieIds.has(m.movie_id));
    const uniqueVectorCandidates = vectorCandidates.filter(m => !mainMovieIds.has(m.movie_id));
    
    // 가중치 비율로 개수 계산 (총 5개)
    const totalCount = 5;
    const keywordCount = Math.round(totalCount * keywordWeight);
    const emotionCount = totalCount - keywordCount;
    
    // 키워드/감성 후보에서 선택
    const selectedKeyword = uniqueKeywordCandidates.slice(0, keywordCount);
    const selectedEmotion = uniqueVectorCandidates.slice(0, emotionCount);
    
    // 합치기
    const additional = [...selectedKeyword, ...selectedEmotion];
    
    // 5개가 안되면 나머지로 채우기
    if (additional.length < totalCount) {
      const remaining = [...uniqueKeywordCandidates, ...uniqueVectorCandidates]
        .filter(m => !additional.find(a => a.movie_id === m.movie_id))
        .slice(0, totalCount - additional.length);
      additional.push(...remaining);
    }
    
    return additional.slice(0, totalCount);
  };

  const additionalRecommendations = getAdditionalRecommendations();

  const handleExplainClick = async (movie: Movie, e: React.MouseEvent) => {
    e.stopPropagation();

    if (loadingExplanations[movie.movie_id]) return;

    if (visibleExplanations[movie.movie_id]) {
      setVisibleExplanations(prev => ({
        ...prev,
        [movie.movie_id]: false
      }));
      return;
    }

    setVisibleExplanations(prev => ({
      ...prev,
      [movie.movie_id]: true
    }));

    if (expandedExplanations[movie.movie_id]) return;

    setLoadingExplanations(prev => ({ ...prev, [movie.movie_id]: true }));

    try {
      const response = await explainRecommendation({
        user_input: input,
        movie_title: movie.title,
        movie_synopsis: movie.synopsis,
        genres: movie.genres,
        keyword_score: movie.keyword_score,
        emotion_score: movie.emotion_score,
        final_score: movie.final_score
      });

      setExpandedExplanations(prev => ({
        ...prev,
        [movie.movie_id]: response.explanation
      }));
    } catch (err) {
      console.error('Explanation error:', err);
      setExpandedExplanations(prev => ({
        ...prev,
        [movie.movie_id]: '설명을 생성하는 중 오류가 발생했습니다.'
      }));
    } finally {
      setLoadingExplanations(prev => ({ ...prev, [movie.movie_id]: false }));
    }
  };

  useEffect(() => {
    const query = searchParams.get('q');
    if (!query) return;
    const trimmed = query.trim();
    if (!trimmed) return;
    if (lastAutoQueryRef.current === trimmed) return;
    lastAutoQueryRef.current = trimmed;
    handleRecommend(trimmed);
  }, [searchParams]);

  return (
    <MainLayout>
      <div className="llm-recommend-page">
        <div className="recommend-container">
          <div className="recommend-header">
            <h1>AI 영화 추천</h1>
            <p>자연어로 원하는 영화를 설명하면 AI가 추천해드립니다.</p>
          </div>


          <div className="search-section">
            <div className="search-box">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="어떤 영화를 찾으시나요? (예: 겨울밤 분위기의 영화)"
                rows={3}
                disabled={isLoading}
              />
             
            <button 
              onClick={handleRecommendClick} 
              disabled={isLoading || (isLoggedIn && !input.trim())}
              className="recommend-btn"
            >
              {isLoading ? '추천 중...' : '추천받기'}
            </button>
            
            {(recommendations.length > 0 || explanation) && (
              <button 
                onClick={handleClear}
                disabled={isLoading}
                className="clear-btn"
                title="결과 지우기"
              >
                ✕
              </button>
            )}
          </div>
          <div className="example-queries">
            <p>예시:</p>
            <button onClick={() => setInput('겨울밤 분위기의 영화')}>
              겨울밤 분위기의 영화
            </button>
            <button onClick={() => setInput('아련한 로맨스 영화')}>
              아련한 로맨스 영화
            </button>
            <button onClick={() => setInput('반전이 있는 영화')}>
              반전이 있는 영화
            </button>
            <button onClick={() => setInput('가족과 함께 보기 좋은 영화')}>
              가족과 함께 보기 좋은 영화
            </button>
          </div>
          {inlineWarning && (
            <p className="ai-inline-warning" key={`ai-warning-${warningTick}`}>
              {inlineWarning}
            </p>
          )}
        </div>
        {error && (
          <div className="error-box">
            <p>오류: {error}</p>
          </div>
        )}

        {isLoading && (
          <div className="loading-box">
            <div className="spinner"></div>
            <p>AI가 영화를 추천하고 있습니다...</p>
          </div>
        )}

        {explanation && !isLoading && (
          <div className="explanation-section">
            <h2>추천 이유</h2>
            <div className="explanation-content">
              {explanation}
            </div>
          </div>
        )}

        {recommendations.length > 0 && !isLoading && (
          <div className="results-section">
            <div className="movie-grid">
              {recommendations.map((movie) => (
                <div key={movie.movie_id} className="movie-card llm-row-card">
                  <button
                    type="button"
                    className="llm-row-poster"
                    onClick={() => handleMovieClick(movie)}
                    aria-label={`${movie.title} 상세 보기`}
                  >
                    {movie.poster_url ? (
                      <img
                        src={movie.poster_url}
                        alt={movie.title}
                        className="movie-poster"
                      />
                    ) : (
                      <div className="movie-poster-placeholder">
                        포스터 없음
                      </div>
                    )}
                  </button>

                  <div
                    className={`llm-pref-card llm-flip-card llm-row-info ${visibleExplanations[movie.movie_id] ? "is-flipped" : ""}`}
                  >
                      <div className="llm-flip-inner">
                        <div className="llm-flip-face llm-flip-front">
                          <div className="movie-info">
                            <h3>{movie.title}</h3>
                            <p className="movie-genres">
                              {movie.release_year} · {movie.genres.join(", ")}
                              {movie.rating && (
                                <span className="movie-rating-inline"> · 평점 {movie.rating.toFixed(1)}</span>
                              )}
                            </p>

                        <div className="llm-satisfaction">
                          <div className="llm-satisfaction-score">
                            💝 내 취향 만족도: {(movie.satisfaction_probability !== undefined
                              ? movie.satisfaction_probability * 100
                              : 0
                            ).toFixed(1)}%
                          </div>
                        </div>

                            <div className="llm-reason-block">
                              <p className="llm-satisfaction-reason">
                                💡 {movie.reason || "추천 이유가 없습니다."}
                              </p>
                            </div>

                            <div className="llm-row-cta">
                              <button
                                className="explain-link"
                                onClick={(e) => handleExplainClick(movie, e)}
                                disabled={loadingExplanations[movie.movie_id]}
                              >
                                {loadingExplanations[movie.movie_id] ? "AI 설명 불러오는 중..." : "AI 상세설명 보기"}
                              </button>
                            </div>
                          </div>
                        </div>
                        <div className="llm-flip-face llm-flip-back">
                          <div className="movie-info">
                            <div className="llm-flip-back-header">
                              <h4>{movie.title}</h4>
                              <button
                                className="explain-link"
                                onClick={(e) => handleExplainClick(movie, e)}
                              >
                                닫기
                              </button>
                            </div>
                            <div className="llm-flip-back-content">
                              {loadingExplanations[movie.movie_id] ? (
                                <p className="muted">설명 생성 중...</p>
                              ) : (
                                <p>{expandedExplanations[movie.movie_id] || "설명이 없습니다."}</p>
                              )}
                            </div>
                          </div>
                        </div>
                      </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 추가 추천 섹션 */}
        {useOrchestrator && !isLoading && additionalRecommendations.length > 0 && (
          <div className="additional-recommendations-wrapper">
            <div className="additional-recommendations-header">
              <h2>✨ 비슷한 키워드 혹은 감성을 가진 영화들 또한 추천드려요</h2>
            </div>
            <div className="additional-movie-grid">
              {additionalRecommendations.map((movie) => (
                <div key={movie.movie_id} className="additional-movie-card" onClick={() => handleMovieClick(movie)}>
                  {movie.poster_url ? (
                    <img 
                      src={movie.poster_url} 
                      alt={movie.title}
                      className="additional-movie-poster"
                    />
                  ) : (
                    <div className="additional-movie-poster-placeholder">
                      포스터 없음
                    </div>
                  )}
                  <div className="additional-movie-info">
                    <h3>{movie.title}</h3>
                    <p className="additional-movie-genres">{movie.genres.join(", ")}</p>

                    {/* 만족도 표시 */}
                    <div className="additional-movie-satisfaction">
                      {movie.satisfaction_probability !== undefined ? (
                        <span className="satisfaction-value">
                          💝 {(movie.satisfaction_probability * 100).toFixed(0)}%
                        </span>
                      ) : (
                        <span className="satisfaction-login-hint">
                          로그인 후 확인
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
        {!isLoading && !error && recommendations.length === 0 && !explanation && (
          <div className="empty-state">
            <div className="empty-icon">MOVIE</div>
            <h3>영화를 추천받아보세요</h3>
            <p>입력창에 원하는 영화나 분위기를 입력해보세요.</p>
          </div>
        )}
      </div>
      </div>
    </MainLayout>
  );
}



