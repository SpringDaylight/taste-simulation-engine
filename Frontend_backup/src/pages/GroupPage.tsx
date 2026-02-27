import { useEffect, useRef, useState } from "react";
import MainLayout from "../components/layout/MainLayout";
import PageTitle from "../components/common/PageTitle";
import { searchGroupUsers, type GroupUserSearchItem } from "../api/A4_group";
import { analyzePreference, simulateGroup, type GroupSimulationResult } from "../api/ml";
import { getCurrentUser } from "../api/users";
import { recommendGroupMovies, type RecommendedMovie, type GroupUser } from "../api/groupRecommend";
import { getAccessToken } from "../api/http";
import { getJsonFromSession, removeSessionItem, setJsonToSession } from "../utils/storage";
import { useTasteSurveyStorage } from "../hooks/useTasteSurveyStorage";

const userRequiredMessage = "회원 사용자를 선택해주세요.";
const maxMembers = 10;
const maxMembersMessage = `최대 ${maxMembers}명까지 선택할 수 있어요.`;
const GROUP_PAGE_SNAPSHOT_KEY = "mw_group_page_snapshot";

type GroupPageSnapshot = {
  userQuery: string;
  selectedMembers: string[];
  selectedMemberProfiles: Record<string, { nickname: string; name: string }>;
  recommendedMovies: RecommendedMovie[];
  groupResult: GroupSimulationResult | null;
  flippedMovies: Record<number, boolean>;
};

// 그룹 추천 설정
const RECOMMEND_TOP_K = 6;  // 추천 영화 개수 (3개, 6개, 10개 등으로 변경 가능)
const RECOMMEND_CANDIDATE_K = 200;  // 후보 영화 개수

const getUserId = (user: GroupUserSearchItem) => user.user_id ?? user.id;
const getUserDisplayName = (user: GroupUserSearchItem) =>
  user.nickname?.trim() || user.user_id?.trim() || user.id;
const getUserSecondaryLabel = (user: GroupUserSearchItem) =>
  user.user_id?.trim() || user.id;

export default function GroupPage() {
  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
  const POSTER_FALLBACK = `data:image/svg+xml;utf8,${encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" width="300" height="450" viewBox="0 0 300 450"><rect width="300" height="450" fill="#F3F6F8"/><rect x="24" y="24" width="252" height="402" rx="16" fill="#FFFFFF" stroke="#A6A8C4"/><text x="150" y="225" text-anchor="middle" fill="#7B7D93" font-family="sans-serif" font-size="18">No Image</text></svg>'
  )}`;
  const resolvePosterUrl = (raw: string) => {
    const trimmed = raw.trim();
    if (!trimmed) return "";
    if (/^(https?:)?\/\//i.test(trimmed)) {
      return trimmed.startsWith("//") ? `https:${trimmed}` : trimmed;
    }
    if (trimmed.startsWith("data:") || trimmed.startsWith("blob:")) {
      return trimmed;
    }
    const base = API_BASE_URL.replace(/\/+$/, "");
    const path = trimmed.startsWith("/") ? trimmed : `/${trimmed}`;
    return `${base}${path}`;
  };
  const [userQuery, setUserQuery] = useState("");
  const [selectedMembers, setSelectedMembers] = useState<string[]>([]);
  const [selectedMemberProfiles, setSelectedMemberProfiles] = useState<
    Record<string, { nickname: string; name: string }>
  >({});
  const [isUserSearchOpen, setIsUserSearchOpen] = useState(false);
  const [recommendedMovies, setRecommendedMovies] = useState<RecommendedMovie[]>([]);
  const [flippedMovies, setFlippedMovies] = useState<Record<number, boolean>>({});
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [errorTick, setErrorTick] = useState(0);
  const [groupResult, setGroupResult] = useState<GroupSimulationResult | null>(null);
  const [userSearchResults, setUserSearchResults] = useState<GroupUserSearchItem[]>([]);
  const [userSearchLoading, setUserSearchLoading] = useState(false);
  const [userSearchError, setUserSearchError] = useState<string | null>(null);
  const [inlineWarning, setInlineWarning] = useState<string | null>(null);
  const [warningTick, setWarningTick] = useState(0);
  const [hasSearchAttempt, setHasSearchAttempt] = useState(false);
  const [currentUserNickname, setCurrentUserNickname] = useState("나");
  const [currentUserId, setCurrentUserId] = useState("");
  const [isLoggedIn, setIsLoggedIn] = useState(() => Boolean(getAccessToken()));
  const userSearchRef = useRef<HTMLDivElement | null>(null);
  const hasAutoSelectedRef = useRef(false);

  useEffect(() => {
    const syncAuthState = () => {
      setIsLoggedIn(Boolean(getAccessToken()));
    };

    syncAuthState();

    const handleAuthChange = () => syncAuthState();
    window.addEventListener("mw_auth_change", handleAuthChange);
    window.addEventListener("storage", handleAuthChange);

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

  useEffect(() => {
    const snapshot = getJsonFromSession<GroupPageSnapshot | null>(
      GROUP_PAGE_SNAPSHOT_KEY,
      null
    );
    if (!snapshot) return;
    if (snapshot.userQuery) setUserQuery(snapshot.userQuery);
    if (snapshot.selectedMembers.length > 0) {
      setSelectedMembers(snapshot.selectedMembers);
    }
    if (Object.keys(snapshot.selectedMemberProfiles).length > 0) {
      setSelectedMemberProfiles(snapshot.selectedMemberProfiles);
    }
    if (snapshot.recommendedMovies.length > 0) {
      setRecommendedMovies(snapshot.recommendedMovies);
    }
    if (snapshot.groupResult) {
      setGroupResult(snapshot.groupResult);
    }
    if (Object.keys(snapshot.flippedMovies).length > 0) {
      setFlippedMovies(snapshot.flippedMovies);
    }
  }, []);
  const tasteSurvey = useTasteSurveyStorage();

  const showError = (message: string) => {
    setError(message);
    setErrorTick((prev) => prev + 1);
  };

  const toggleFlip = (movieId: number) => {
    setFlippedMovies((prev) => ({
      ...prev,
      [movieId]: !prev[movieId],
    }));
  };

  useEffect(() => {
    if (!isLoggedIn) return;
    let isCancelled = false;
    getCurrentUser()
      .then((user) => {
        if (isCancelled) return;
        const name =
          user.nickname?.trim() ||
          user.name?.trim() ||
          user.user_id?.trim() ||
          user.id;
        setCurrentUserId(user.user_id ?? user.id);
        setCurrentUserNickname(name || "나");
      })
      .catch((err) => {
        console.error("Failed to load current user:", err);
        if (!isCancelled) {
          setCurrentUserId("");
          setCurrentUserNickname("나");
        }
      });

    return () => {
      isCancelled = true;
    };
  }, [isLoggedIn]);

  const userRequiredError = error === userRequiredMessage ? error : null;
  const formError =
    error && error !== userRequiredMessage
      ? error
      : null;

  const userResults = userSearchResults.filter(
    (user) => !selectedMembers.includes(getUserId(user))
  );

  const selectedMemberItems = selectedMembers.map((memberId) => {
    const cached = selectedMemberProfiles[memberId];
    const latest = userSearchResults.find((user) => getUserId(user) === memberId);
    const nickname =
      cached?.nickname || (latest ? getUserDisplayName(latest) : memberId);
    return {
      id: memberId,
      nickname,
    };
  });

  useEffect(() => {
    if (!isLoggedIn || !currentUserId || hasAutoSelectedRef.current) return;
    setSelectedMembers((prev) => {
      if (prev.includes(currentUserId)) return prev;
      return [currentUserId, ...prev];
    });
    setSelectedMemberProfiles((prev) => ({
      ...prev,
      [currentUserId]: {
        nickname: currentUserNickname,
        name: currentUserNickname,
      },
    }));
    hasAutoSelectedRef.current = true;
  }, [currentUserId, currentUserNickname, isLoggedIn]);

  useEffect(() => {
    const snapshot: GroupPageSnapshot = {
      userQuery,
      selectedMembers,
      selectedMemberProfiles,
      recommendedMovies,
      groupResult,
      flippedMovies,
    };
    setJsonToSession(GROUP_PAGE_SNAPSHOT_KEY, snapshot);
  }, [
    userQuery,
    selectedMembers,
    selectedMemberProfiles,
    recommendedMovies,
    groupResult,
    flippedMovies,
  ]);

  const handleMemberToggle = (userId: string, profile?: { nickname: string; name: string }) => {
    const alreadySelected = selectedMembers.includes(userId);
    if (alreadySelected) {
      setSelectedMembers((prev) => prev.filter((id) => id !== userId));
      setSelectedMemberProfiles((prev) => {
        const next = { ...prev };
        delete next[userId];
        return next;
      });
      return;
    }

    if (selectedMembers.length >= maxMembers) {
      showError(maxMembersMessage);
      return;
    }

    setSelectedMembers((prev) => [...prev, userId]);
    if (profile) {
      setSelectedMemberProfiles((prev) => ({
        ...prev,
        [userId]: profile,
      }));
    }

    if (userRequiredError) {
      setError(null);
    }
  };

  useEffect(() => {
    const handleOutsideClick = (event: MouseEvent) => {
      if (!(event.target instanceof Node)) return;

      if (userSearchRef.current && !userSearchRef.current.contains(event.target)) {
        setIsUserSearchOpen(false);
      }
    };

    document.addEventListener("mousedown", handleOutsideClick);
    return () => {
      document.removeEventListener("mousedown", handleOutsideClick);
    };
  }, []);

  useEffect(() => {
    if (!isUserSearchOpen) {
      setUserSearchResults([]);
      setUserSearchError(null);
      setUserSearchLoading(false);
      setHasSearchAttempt(false);
      return;
    }
    if (!isLoggedIn) {
      setUserSearchResults([]);
      setUserSearchError(null);
      setUserSearchLoading(false);
      setHasSearchAttempt(false);
      return;
    }
    if (!userQuery.trim()) {
      setUserSearchResults([]);
      setUserSearchError(null);
      setUserSearchLoading(false);
      setHasSearchAttempt(false);
      return;
    }

    let isCancelled = false;
    const timer = setTimeout(() => {
      setUserSearchLoading(true);
      setHasSearchAttempt(true);
      searchGroupUsers(userQuery, 20)
        .then((results) => {
          if (isCancelled) return;
          setUserSearchResults(results);
          setUserSearchError(null);
        })
        .catch((err) => {
          if (isCancelled) return;
          console.error("Failed to search users:", err);
          const message =
            err instanceof Error && err.message
              ? err.message
              : "사용자 조회에 실패했습니다.";
          setUserSearchResults([]);
          setUserSearchError(message);
        })
        .finally(() => {
          if (isCancelled) return;
          setUserSearchLoading(false);
        });
    }, 250);

    return () => {
      isCancelled = true;
      clearTimeout(timer);
    };
  }, [isUserSearchOpen, userQuery, isLoggedIn]);

  const handleAnalyze = async () => {
    if (!isLoggedIn) {
      showInlineWarning("로그인 후 이용해주세요.");
      return;
    }
    if (selectedMembers.length < 2) {
      showError("회원 사용자를 2명 이상 선택해주세요.");
      return;
    }

    console.log('[그룹 추천 시작]', {
      memberCount: selectedMembers.length,
      timestamp: new Date().toISOString()
    });
    const startTime = Date.now();

    setAnalyzing(true);
    setError(null);

    try {
      const likedGenres = tasteSurvey.selectedGenres;
      const avoidedGenres = tasteSurvey.avoidedGenres;
      const keywords = tasteSurvey.savedKeywords;
      const vibe = tasteSurvey.savedVibe;
      const context = tasteSurvey.tasteContext;
      const origin = tasteSurvey.tasteOrigin;

      const tasteText = [
        vibe,
        context,
        origin,
        ...likedGenres,
        ...keywords,
      ]
        .map((value) => value.trim())
        .filter(Boolean)
        .join(" ");

      const neutralProfile = {
        emotion_scores: {},
        narrative_traits: {},
        ending_preference: { happy: 0.33, open: 0.33, bittersweet: 0.34 },
      };

      let baseProfile = neutralProfile;
      try {
        const analyzed = await analyzePreference({
          text: tasteText || "기본 취향",
          dislikes: avoidedGenres.join(", "),
        });
        baseProfile = {
          emotion_scores: analyzed.emotion_scores,
          narrative_traits: analyzed.narrative_traits,
          ending_preference: analyzed.ending_preference,
        };
      } catch (analysisError) {
        console.error("Failed to analyze preference, using neutral profile:", analysisError);
      }

      const membersPayload = selectedMembers.map((memberId) => {
        const isMe = currentUserId && memberId === currentUserId;
        const label =
          (isMe ? currentUserNickname : selectedMemberProfiles[memberId]?.nickname) ||
          memberId;
        return {
          user_id: label,
          profile: isMe ? baseProfile : neutralProfile,
          likes: isMe ? likedGenres : [],
          dislikes: isMe ? avoidedGenres : [],
        };
      });

      const groupSimulation = await simulateGroup({
        members: membersPayload as any,
        movie_profile: baseProfile as any,
        strategy: "least_misery",
      });
      setGroupResult(groupSimulation as GroupSimulationResult);

      // 사용자 데이터 구성 (영화 추천용)
      const users: GroupUser[] = selectedMembers.map((memberId) => {
        const isMe = currentUserId && memberId === currentUserId;
        const label =
          (isMe ? currentUserNickname : selectedMemberProfiles[memberId]?.nickname) ||
          memberId;
        return {
          user_id: memberId,  // 실제 user_id 사용 (nickname이 아님)
          name: label,
          text: isMe ? keywords.join(", ") : "",
          likes: isMe ? likedGenres : [],
          dislikes: isMe ? avoidedGenres : [],
        };
      });

      console.log('[API 호출 시작]', {
        users: users.length,
        top_k: RECOMMEND_TOP_K,
        candidate_k: RECOMMEND_CANDIDATE_K
      });

      // 백엔드 API 호출
      const response = await recommendGroupMovies({
        users,
        top_k: RECOMMEND_TOP_K,
        candidate_k: RECOMMEND_CANDIDATE_K,
        strategy: 'mean',
        use_bedrock: true
      });

      const elapsed = ((Date.now() - startTime) / 1000).toFixed(2);
      console.log('[그룹 추천 완료]', {
        movies: response.topk.length,
        candidates: response.candidates_count,
        elapsed: `${elapsed}초`
      });

      setRecommendedMovies(response.topk);
    } catch (err) {
      const elapsed = ((Date.now() - startTime) / 1000).toFixed(2);
      console.error('[그룹 추천 실패]', {
        error: err,
        elapsed: `${elapsed}초`
      });
      
      let errorMessage = "그룹 분석에 실패했습니다.";
      if (err instanceof Error) {
        errorMessage = err.message;
      }
      
      showError(errorMessage);
    } finally {
      setAnalyzing(false);
    }
  };

  const handleReset = () => {
    setUserQuery("");
    setSelectedMembers([]);
    setSelectedMemberProfiles({});
    setRecommendedMovies([]);
    setGroupResult(null);
    setFlippedMovies({});
    setUserSearchResults([]);
    setUserSearchError(null);
    setUserSearchLoading(false);
    setIsUserSearchOpen(false);
    setError(null);
    setInlineWarning(null);
    removeSessionItem(GROUP_PAGE_SNAPSHOT_KEY);
  };

  const canReset = isLoggedIn && recommendedMovies.length > 0;
  const inlineSearchMessage = inlineWarning
    ? inlineWarning
    : userSearchError
      ? userSearchError
      : isUserSearchOpen &&
          hasSearchAttempt &&
          !userSearchLoading &&
          userQuery.trim().length > 0 &&
          userSearchResults.length === 0
        ? "검색 결과가 없습니다."
        : null;
  const shouldShowMemberPanel =
    selectedMembers.length > 0 || Boolean(formError) || Boolean(userRequiredError);

  return (
    <MainLayout>
      <main className="container group-page">
        <PageTitle
          title="모두가 만족하는 영화 찾기"
          description="모임 구성원들의 취향을 한 번에 정리해드려요."
        />

        <section className="section card">
          <div className="form-grid">
            <div className="group-search-column">
              <div className="group-search-field">
                <label>영화 같이 볼 회원 검색하기
                  (최대 10명까지 검색 가능해요)</label>
                <div className="group-search-row">
                  <div className="group-search-input" ref={userSearchRef}>
                    <input
                      type="text"
                      placeholder="이름/닉네임/아이디로 검색하세요"
                      value={userQuery}
                      onClick={() => {
                        setIsUserSearchOpen(true);
                        if (!isLoggedIn) showInlineWarning("로그인 후 이용해주세요.");
                      }}
                      onFocus={() => {
                        setIsUserSearchOpen(true);
                        if (!isLoggedIn) showInlineWarning("로그인 후 이용해주세요.");
                      }}
                      onChange={(event) => {
                        if (!isLoggedIn) {
                          showInlineWarning("로그인 후 이용해주세요.");
                          return;
                        }
                        setInlineWarning(null);
                        setUserQuery(event.target.value);
                      }}
                    />
                    {isUserSearchOpen &&
                      isLoggedIn &&
                      (userSearchLoading || userResults.length > 0) && (
                        <div className="search-results group-user-results">
                          {userSearchLoading && (
                            <div className="search-empty">사용자를 조회하는 중입니다.</div>
                          )}
                          {!userSearchLoading &&
                            userResults.map((user) => {
                              const userId = getUserId(user);
                              const nickname = getUserDisplayName(user);
                              const secondary = getUserSecondaryLabel(user);
                              return (
                                <button
                                  className={`search-item ${
                                    selectedMembers.includes(userId) ? "active" : ""
                                  }`}
                                  type="button"
                                  key={userId}
                                  onClick={() =>
                                    handleMemberToggle(userId, {
                                      nickname,
                                      name: secondary || nickname,
                                    })
                                  }
                                >
                                  <strong>{nickname}</strong>
                                  <span>{secondary}</span>
                                  {selectedMembers.includes(userId) && <span>✓</span>}
                                </button>
                              );
                            })}
                        </div>
                      )}
                  </div>
                  <div className="group-action-stack">
                    <button
                      className="primary-btn group-analyze-btn"
                      onClick={handleAnalyze}
                      disabled={analyzing}
                      type="button"
                    >
                      {analyzing ? "추천 받는 중..." : "추천받기"}
                    </button>
                    {canReset && (
                      <button
                        className="secondary-btn group-reset-btn"
                        onClick={handleReset}
                        disabled={analyzing || !canReset}
                        type="button"
                      >
                        초기화
                      </button>
                    )}
                  </div>
                </div>
                {inlineSearchMessage && (
                  <p className="group-inline-warning" key={`group-warning-${warningTick}`}>
                    {inlineSearchMessage}
                  </p>
                )}
              </div>

              {shouldShowMemberPanel && (
                <div className="group-selected-members is-inline">
                  {selectedMemberItems.length > 0 && (
                    <div className="tag-list">
                      {selectedMemberItems.map((member) => (
                        <span key={member.id} className="tag group-selected-tag">
                          {member.nickname}
                          <button
                            className="group-selected-remove"
                            type="button"
                            aria-label={`${member.nickname} 선택 해제`}
                            onClick={() => handleMemberToggle(member.id)}
                          >
                            ×
                          </button>
                        </span>
                      ))}
                    </div>
                  )}
                  <p className="muted">선택된 회원: {selectedMembers.length}명</p>
                  {(formError || userRequiredError) && (
                    <p className="error" key={`member-error-${errorTick}`}>
                      {formError || userRequiredError}
                    </p>
                  )}
                </div>
              )}
            </div>
            
            {analyzing && (
              <p className="muted" style={{ marginTop: 8, fontSize: "0.9em" }}>
                💡 영화 데이터를 분석하고 있습니다. 잠시만 기다려주세요.
              </p>
            )}
          </div>
        </section>

        {analyzing && (
          <div className="loading-box">
            <div className="spinner"></div>
            <p>AI가 영화를 추천하고 있습니다...</p>
          </div>
        )}

        {recommendedMovies.length > 0 && !analyzing && (
          <section className="section">
            <h2>추천 영화 ({recommendedMovies.length}개)</h2>
            <div className="group-result-grid">
              {recommendedMovies.map((movie) => (
                <article
                  key={movie.movie_id}
                  className={`card group-flip-card ${flippedMovies[movie.movie_id] ? "is-flipped" : ""}`}
                  role="button"
                  tabIndex={0}
                  onClick={() => toggleFlip(movie.movie_id)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      toggleFlip(movie.movie_id);
                    }
                  }}
                >
                  <div className="group-flip-inner">
                    <div className="group-flip-face group-flip-front">
                      <div className="group-movie-card">
                        {(() => {
                          const rawPoster = String(
                            movie.poster_url ||
                              (movie as unknown as { posterUrl?: string | null }).posterUrl ||
                              (movie as unknown as { poster_path?: string | null }).poster_path ||
                              (movie as unknown as { poster?: string | null }).poster ||
                              ""
                          ).trim();
                          const posterSrc = rawPoster ? resolvePosterUrl(rawPoster) : "";
                          return posterSrc ? (
                            <img
                              className="group-movie-poster"
                              src={posterSrc}
                              alt={`${movie.title} 포스터`}
                              loading="lazy"
                              onError={(event) => {
                                const target = event.currentTarget;
                                target.onerror = null;
                                target.src = POSTER_FALLBACK;
                              }}
                            />
                          ) : (
                            <img
                              className="group-movie-poster is-empty"
                              src={POSTER_FALLBACK}
                              alt=""
                              aria-hidden="true"
                            />
                          );
                        })()}
                        <div className="movie-info">
                          <h3>
                            <a
                              className="group-movie-title-link"
                              href={`/movies/${movie.movie_id}`}
                              onClick={(event) => event.stopPropagation()}
                            >
                              {movie.title}
                            </a>
                          </h3>
                          <p className="muted">
                            {movie.release_year} · {movie.genres.join(", ")}
                          </p>
                          <p className="probability">
                            그룹 만족도: {Math.round(movie.group_score * 100)}%
                          </p>
                        </div>
                      </div>
                    </div>
                    <div className="group-flip-face group-flip-back">
                      <div className="group-flip-back-header">
                        <h4>멤버별 예상 반응</h4>
                      </div>
                      <div className="group-flip-back-content">
                        {movie.per_user_detail && movie.per_user_detail.length > 0 ? (
                          movie.per_user_detail.map((detail) => (
                            <div key={detail.user_id} className="group-user-reaction">
                              <p>
                                <strong>{detail.name}</strong>: {Math.round(detail.probability * 100)}%
                              </p>
                              <p className="muted">{detail.explanation}</p>
                              {detail.top_factors.length > 0 && (
                                <p className="muted">
                                  주요 요인: {detail.top_factors.join(", ")}
                                </p>
                              )}
                            </div>
                          ))
                        ) : (
                          <p className="muted">멤버별 반응 데이터가 없습니다.</p>
                        )}
                      </div>
                    </div>
                  </div>
                </article>
              ))}
            </div>
          </section>
        )}
      </main>
    </MainLayout>
  );
}
