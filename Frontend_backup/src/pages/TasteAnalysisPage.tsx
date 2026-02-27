import { useEffect, useRef, useState, type CSSProperties } from "react";
import { Link, useNavigate } from "react-router-dom";
import MainLayout from "../components/layout/MainLayout";
import TasteSurveyModal from "../components/TasteSurveyModal";
import PageTitle from "../components/common/PageTitle";
import SectionHeader from "../components/common/SectionHeader";
import MovieTileCard from "../components/movie/MovieTileCard";
import LoadingState from "../components/common/LoadingState";
import EmptyState from "../components/common/EmptyState";
import { getMovie } from "../api/A2_movies";
import { getCurrentUser, getCurrentUserReviews } from "../api/A7_profile";
import { getCurrentUserWatchedMovies } from "../api/A8_watched";
import { getTasteMap, type UserProfile } from "../api/ml";
import { getUserPreference } from "../api/userPreferences";
import { getAccessToken } from "../api/http";
import { getStorageItem, safeParseJson } from "../utils/storage";
import { useTasteSurveyStorage } from "../hooks/useTasteSurveyStorage";

type RecentMovie = {
  movieId: number;
  title: string;
  poster: string;
};

const POSTER_FALLBACK = "https://via.placeholder.com/500x750?text=No+Image";

const getFillStyle = (percent: number): CSSProperties =>
  ({ ["--fill" as string]: `${percent}%` } as CSSProperties);

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export default function TasteAnalysisPage() {
  const navigate = useNavigate();
  const [userProfile, setUserProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [recentHighRated, setRecentHighRated] = useState<RecentMovie[]>([]);
  const [reviewsLoading, setReviewsLoading] = useState(false);
  const [watchedGenreStats, setWatchedGenreStats] = useState<
    Array<{ genre: string; percent: number }>
  >([]);
  const [isSurveyOpen, setIsSurveyOpen] = useState(false);
  const [surveyRefreshKey, setSurveyRefreshKey] = useState(0);
  const [currentUserId, setCurrentUserId] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState<number | null>(null);
  
  // Survey data from DB
  const [surveyData, setSurveyData] = useState<{
    favorite_genres: string[];
    disliked_genres: string[];
    viewing_context: string;
    preferred_vibe: string;
    interest_keywords: string[];
    preferred_origin: string;
  } | null>(null);
  
  // WordCloud state
  const [wordCloudUserId, setWordCloudUserId] = useState<string | null>(null);
  const [wordCloudLoading, setWordCloudLoading] = useState(false);
  const [wordCloudError, setWordCloudError] = useState<string | null>(null);
  const [wordCloudUrl, setWordCloudUrl] = useState<string | null>(null);
  const wordCloudUrlRef = useRef<string | null>(null);
  const [isLoggedIn, setIsLoggedIn] = useState(() => Boolean(getAccessToken()));

  useEffect(() => {
    const syncAuthState = () => {
      setIsLoggedIn(Boolean(getAccessToken()));
    };

    syncAuthState();

    const handleStorage = (event: StorageEvent) => {
      if (!event.key || event.key === "mw_access_token") {
        syncAuthState();
      }
    };

    window.addEventListener("storage", handleStorage);
    window.addEventListener("mw_auth_change", syncAuthState);

    const interval = window.setInterval(syncAuthState, 4000);

    return () => {
      window.removeEventListener("storage", handleStorage);
      window.removeEventListener("mw_auth_change", syncAuthState);
      window.clearInterval(interval);
    };
  }, []);

  useEffect(() => {
    if (!isLoggedIn) {
      navigate("/", { replace: true });
    }
  }, [isLoggedIn, navigate]);

  const handleSurveyOpen = () => setIsSurveyOpen(true);
  const handleSurveyClose = () => setIsSurveyOpen(false);
  const handleSurveyComplete = () => {
    setIsSurveyOpen(false);
    setSurveyRefreshKey((prev) => prev + 1);
  };

  useEffect(() => {
    const loadTasteAnalysis = async () => {
      setLoading(true);
      try {
        if (isLoggedIn) {
          const currentUser = await getCurrentUser();
          setCurrentUserId(currentUser.id.toString());
          setWordCloudUserId(currentUser.id.toString());
          const preference = await getUserPreference(currentUser.id);
          
          // Survey data 저장
          setSurveyData({
            favorite_genres: preference.favorite_genres || [],
            disliked_genres: preference.disliked_genres || [],
            viewing_context: preference.viewing_context || "",
            preferred_vibe: preference.preferred_vibe || "",
            interest_keywords: preference.interest_keywords || [],
            preferred_origin: preference.preferred_origin || "",
          });
          
          const topEmotions = Object.entries(preference.preference_vector_json.emotion_scores)
            .sort(([, a], [, b]) => b - a)
            .slice(0, 3)
            .map(([tag]) => tag);
          const topNarratives = Object.entries(
            preference.preference_vector_json.narrative_traits
          )
            .sort(([, a], [, b]) => b - a)
            .slice(0, 3)
            .map(([tag]) => tag);

          const userText = [...topEmotions, ...topNarratives].join(", ");
          const profile: UserProfile = {
            user_text: userText,
            emotion_scores: preference.preference_vector_json.emotion_scores,
            narrative_traits: preference.preference_vector_json.narrative_traits,
            direction_mood: preference.preference_vector_json.direction_mood,
            character_relationship: preference.preference_vector_json.character_relationship,
            ending_preference: preference.preference_vector_json.ending_preference,
            dislike_tags: preference.penalty_tags ?? [],
            boost_tags: preference.boost_tags ?? [],
          };
          setUserProfile(profile);
          if (userText) {
            await getTasteMap({
              user_text: userText,
              k: 8,
            });
          }
        } else {
          setWordCloudUserId(null);
          setSurveyData(null);
          const savedProfile = getStorageItem("mw_user_profile");
          if (savedProfile) {
            const profile = safeParseJson<UserProfile | null>(savedProfile, null);
            if (!profile) return;
            setUserProfile(profile);
            if (profile.user_text) {
              await getTasteMap({
                user_text: profile.user_text,
                k: 8,
              });
            }
          }
        }
      } catch (err) {
        console.error("Failed to load taste analysis:", err);
      } finally {
        setLoading(false);
      }
    };

    loadTasteAnalysis();
  }, [isLoggedIn, surveyRefreshKey]);

  useEffect(() => {
    if (!isLoggedIn || !wordCloudUserId) {
      setWordCloudError(null);
      setWordCloudLoading(false);
      if (wordCloudUrlRef.current) {
        URL.revokeObjectURL(wordCloudUrlRef.current);
        wordCloudUrlRef.current = null;
      }
      setWordCloudUrl(null);
      return;
    }

    let isCancelled = false;
    const controller = new AbortController();

    const fetchWordCloud = async () => {
      setWordCloudLoading(true);
      setWordCloudError(null);

      try {
        const token = getAccessToken();
        const response = await fetch(
          `${API_BASE_URL}/api/user-preferences/${wordCloudUserId}/wordcloud?type=boost`,
          {
            method: "GET",
            headers: token ? { Authorization: `Bearer ${token}` } : undefined,
            credentials: "include",
            signal: controller.signal,
          }
        );

        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(errorText || "워드 클라우드를 불러오지 못했습니다.");
        }

        const blob = await response.blob();
        const nextUrl = URL.createObjectURL(blob);
        if (isCancelled) {
          URL.revokeObjectURL(nextUrl);
          return;
        }

        if (wordCloudUrlRef.current) {
          URL.revokeObjectURL(wordCloudUrlRef.current);
        }
        wordCloudUrlRef.current = nextUrl;
        setWordCloudUrl(nextUrl);
      } catch (err) {
        if (isCancelled) return;
        console.error("Failed to fetch word cloud:", err);
        setWordCloudError("워드 클라우드 데이터를 불러오지 못했습니다.");
        if (wordCloudUrlRef.current) {
          URL.revokeObjectURL(wordCloudUrlRef.current);
          wordCloudUrlRef.current = null;
        }
        setWordCloudUrl(null);
      } finally {
        if (!isCancelled) setWordCloudLoading(false);
      }
    };

    fetchWordCloud();

    return () => {
      isCancelled = true;
      controller.abort();
    };
  }, [isLoggedIn, wordCloudUserId]);

  useEffect(() => {
    if (!isLoggedIn) {
      setRecentHighRated([]);
      return;
    }

    let isCancelled = false;

    const fetchHighRated = async () => {
      setReviewsLoading(true);
      try {
        const reviewResponse = await getCurrentUserReviews({
          page: 1,
          page_size: 100,
        });
        if (isCancelled) return;

        const reviews = Array.isArray(reviewResponse?.reviews)
          ? reviewResponse.reviews
          : [];
        const sorted = [...reviews].sort(
          (a, b) =>
            new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
        );

        const filtered = sorted.filter((review) => Number(review.rating) >= 4.5);
        const uniqueByMovie = new Map<number, typeof filtered[number]>();
        filtered.forEach((review) => {
          if (!uniqueByMovie.has(review.movie_id)) {
            uniqueByMovie.set(review.movie_id, review);
          }
        });

        const selected = Array.from(uniqueByMovie.values()).slice(0, 4);
        const movies = await Promise.all(
          selected.map(async (review) => {
            try {
              const movie = await getMovie(review.movie_id);
              return {
                movieId: review.movie_id,
                title: movie.title || `?곹솕 #${review.movie_id}`,
                poster: movie.poster_url || POSTER_FALLBACK,
              };
            } catch (movieErr) {
              console.error(
                `Failed to fetch movie detail for movie_id=${review.movie_id}:`,
                movieErr
              );
              return {
                movieId: review.movie_id,
                title: `?곹솕 #${review.movie_id}`,
                poster: POSTER_FALLBACK,
              };
            }
          })
        );

        if (isCancelled) return;
        setRecentHighRated(movies);
      } catch (err) {
        if (isCancelled) return;
        console.error("Failed to fetch high rated reviews:", err);
        setRecentHighRated([]);
      } finally {
        if (!isCancelled) setReviewsLoading(false);
      }
    };

    fetchHighRated();

    return () => {
      isCancelled = true;
    };
  }, [isLoggedIn]);

  useEffect(() => {
    if (!isLoggedIn) {
      setWatchedGenreStats([]);
      return;
    }

    let isCancelled = false;

    const fetchWatchedGenreStats = async () => {
      let apiItems: Array<{
        movie_id: number;
        user_id?: string | null;
        genres?: string[] | null;
      }> = [];
      try {
        const response = await getCurrentUserWatchedMovies({
          page: 1,
          page_size: 100,
        });
        if (isCancelled) return;
        apiItems = response.items;
      } catch (err) {
        console.error("Failed to fetch watched movies from API:", err);
      }

      if (isCancelled) return;

      const movieIds = Array.from(
        new Set(apiItems.map((item) => Number(item.movie_id)))
      ).filter((id) => Number.isFinite(id));

      if (movieIds.length === 0) {
        setWatchedGenreStats([]);
        return;
      }

      const genreCounts = new Map<string, number>();
      const needsFetch = new Set<number>();
      apiItems.forEach((item) => {
        const movieId = Number(item.movie_id);
        if (!Number.isFinite(movieId)) return;
        const genres = Array.isArray(item.genres) ? item.genres : [];
        if (genres.length === 0) {
          needsFetch.add(movieId);
          return;
        }
        genres.forEach((genre) => {
          if (typeof genre !== "string") return;
          const trimmed = genre.trim();
          if (!trimmed) return;
          genreCounts.set(trimmed, (genreCounts.get(trimmed) ?? 0) + 1);
        });
      });

      await Promise.all(
        Array.from(needsFetch).map(async (movieId) => {
          try {
            const movie = await getMovie(movieId);
            if (!movie?.genres) return;
            movie.genres.forEach((genre) => {
              if (typeof genre !== "string") return;
              const trimmed = genre.trim();
              if (!trimmed) return;
              genreCounts.set(trimmed, (genreCounts.get(trimmed) ?? 0) + 1);
            });
          } catch (err) {
            console.error(
              `Failed to fetch movie genres for movie_id=${movieId}:`,
              err
            );
          }
        })
      );

      if (isCancelled) return;

      if (genreCounts.size === 0) {
        setWatchedGenreStats([]);
        return;
      }

      const totalMovies = movieIds.length;
      const topGenres = Array.from(genreCounts.entries())
        .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0], "ko-KR"))
        .slice(0, 5)
        .map(([genre, count]) => ({
          genre,
          percent: Math.round((count / totalMovies) * 100),
        }));

      setWatchedGenreStats(topGenres);
    };

    fetchWatchedGenreStats();

    return () => {
      isCancelled = true;
    };
  }, [isLoggedIn]);

  const getWordCloudUrl = () => {
    if (!currentUserId || !isLoggedIn) return null;
    let url = `${import.meta.env.VITE_API_BASE_URL || "http://localhost:8000"}/api/user-preferences/${currentUserId}/wordcloud?type=both`;
    if (refreshKey) {
      url += `&t=${refreshKey}`;
    }
    return url;
  };
  const computedWordCloudUrl = getWordCloudUrl();
  const emotionWordCloudUrl = computedWordCloudUrl ? computedWordCloudUrl.replace("type=both", "type=emotion") : null;

  const handleRefreshWordCloud = () => {
    setRefreshKey(Date.now());
  };

  const {
    savedKeywords,
    savedVibe,
    selectedGenres,
    avoidedGenres,
    tasteContext,
    tasteOrigin,
    hasSurveyData: hasStorageSurveyData,
  } = useTasteSurveyStorage(surveyRefreshKey);
  
  // DB 데이터 우선, 없으면 localStorage fallback
  const displaySurveyData = surveyData ? {
    favorite_genres: surveyData.favorite_genres || [],
    disliked_genres: surveyData.disliked_genres || [],
    viewing_context: surveyData.viewing_context || "",
    preferred_vibe: surveyData.preferred_vibe 
      ? surveyData.preferred_vibe.split("/").map(v => v.trim()).filter(v => v.length > 0)
      : [],
    interest_keywords: surveyData.interest_keywords || [],
    preferred_origin: surveyData.preferred_origin || "",
  } : {
    favorite_genres: selectedGenres,
    disliked_genres: avoidedGenres,
    viewing_context: tasteContext,
    preferred_vibe: savedVibe ? [savedVibe] : [],
    interest_keywords: savedKeywords,
    preferred_origin: tasteOrigin,
  };
  
  const hasSurveyData = Boolean(userProfile) || Boolean(surveyData) || hasStorageSurveyData;
  const preferenceSlots = Array.from({ length: 5 }, (_, index) => {
    const slot = watchedGenreStats[index];
    if (!slot) {
      return { genre: "미설정", percent: 0 };
    }
    return { genre: slot.genre, percent: slot.percent };
  });

  if (!isLoggedIn) {
    return null;
  }

  if (loading) {
    return (
      <MainLayout>
        <main className="container taste-analysis-page">
          <LoadingState message="취향 분석 중..." />
        </main>
      </MainLayout>
    );
  }

  return (
    <MainLayout>
      <main className="container taste-analysis-page">
        <PageTitle
          title="취향 분석 상세"
          description="나의 영화 취향을 확인해보세요!"
        />

        <section className="section card taste-preview-section">
          <article className="taste-preview">
            <div className="taste-preview-header with-cta">
              <div>
                <h2>나의 영화 취향 설문 결과</h2>
                <p>설문 답변 요약</p>
              </div>
              {hasSurveyData && (
                <button
                  className="secondary-btn taste-preview-top-cta"
                  type="button"
                  onClick={handleSurveyOpen}
                >
                  취향설문 다시하기
                </button>
              )}
            </div>
            <div className="taste-preview-body">
              {hasSurveyData ? (
                <div className="survey-summary-grid">
                  <div className="survey-summary-card">
                    <h3 className="survey-summary-title">좋아하는 장르</h3>
                    {displaySurveyData.favorite_genres.length > 0 ? (
                      <div className="tag-list">
                        {displaySurveyData.favorite_genres.map((genre) => (
                          <span key={genre} className="tag">
                            {genre}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <p className="survey-summary-value is-empty">미설정</p>
                    )}
                  </div>
                  <div className="survey-summary-card">
                    <h3 className="survey-summary-title">싫어하는 장르</h3>
                    {displaySurveyData.disliked_genres.length > 0 ? (
                      <div className="tag-list">
                        {displaySurveyData.disliked_genres.map((genre) => (
                          <span key={genre} className="tag">
                            {genre}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <p className="survey-summary-value is-empty">미설정</p>
                    )}
                  </div>
                  <div className="survey-summary-card">
                    <h3 className="survey-summary-title">주로 영화를 볼 때에는?</h3>
                    {displaySurveyData.viewing_context ? (
                      <div className="tag-list">
                        <span className="tag">{displaySurveyData.viewing_context}</span>
                      </div>
                    ) : (
                      <p className="survey-summary-value is-empty">미설정</p>
                    )}
                  </div>
                  <div className="survey-summary-card">
                    <h3 className="survey-summary-title">좋아하는 분위기</h3>
                    {displaySurveyData.preferred_vibe.length > 0 ? (
                      <div className="tag-list">
                        {displaySurveyData.preferred_vibe.map((vibe) => (
                          <span key={vibe} className="tag">{vibe}</span>
                        ))}
                      </div>
                    ) : (
                      <p className="survey-summary-value is-empty">미설정</p>
                    )}
                  </div>
                  <div className="survey-summary-card">
                    <h3 className="survey-summary-title">좋아하는 소재</h3>
                    {displaySurveyData.interest_keywords.length > 0 ? (
                      <div className="tag-list">
                        {displaySurveyData.interest_keywords.map((keyword) => (
                          <span key={keyword} className="tag">
                            {keyword}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <p className="survey-summary-value is-empty">미설정</p>
                    )}
                  </div>
                  <div className="survey-summary-card">
                    <h3 className="survey-summary-title">좋아하는 영화 나라</h3>
                    {displaySurveyData.preferred_origin ? (
                      <div className="tag-list">
                        <span className="tag">{displaySurveyData.preferred_origin}</span>
                      </div>
                    ) : (
                      <p className="survey-summary-value is-empty">미설정</p>
                    )}
                  </div>
                </div>
              ) : (
                <div className="survey-summary-empty">
                  <p>취향분석 설문에 참여해주세요.</p>
                </div>
              )}
            </div>
          </article>
        </section>
        {!hasSurveyData && (
          <div className="survey-cta-row">
            <button
              className="icon-btn page-arrow-btn survey-cta-btn"
              type="button"
              onClick={handleSurveyOpen}
            >
              설문 참여하기
            </button>
          </div>
        )}

        <section className="section card taste-preview-section">
          <article className="taste-preview">
            <div className="taste-preview-header with-cta" style={{ position: 'relative' }}>
              <div>
                <h2>취향 대시보드</h2>
                {/* <p>워드 클라우드 분석 결과</p> */}
              </div>
              <button
                type="button"
                onClick={handleRefreshWordCloud}
                style={{
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                  padding: '8px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#6b7280',
                  transition: 'color 0.2s ease, transform 0.2s ease',
                  position: 'absolute',
                  top: '16px',
                  right: '16px',
                }}
                title="최신 데이터 반영하기"
                onMouseEnter={(e) => {
                  e.currentTarget.style.color = '#3b82f6';
                  e.currentTarget.style.transform = 'rotate(15deg)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.color = '#6b7280';
                  e.currentTarget.style.transform = 'rotate(0deg)';
                }}
                aria-label="새로고침"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
                  <path d="M3 3v5h5" />
                </svg>
              </button>
            </div>
            <div className="taste-preview-body taste-preview-grid">
              <div className="taste-preview-main">
                <p className="muted">정서 취향</p>
                {emotionWordCloudUrl ? (
                  <div className="word-cloud-image-container" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", padding: "16px" }}>
                    <img
                      src={emotionWordCloudUrl}
                      alt="선호 정서 워드 클라우드"
                      style={{ width: "100%", maxWidth: "500px", height: "auto", borderRadius: "8px", objectFit: "contain" }}
                      onError={(e) => {
                        (e.target as HTMLImageElement).style.display = 'none';
                        (e.target as HTMLImageElement).parentElement!.innerHTML = '<p class="muted">정서 데이터를 불러올 수 없습니다.<br/>(리뷰 데이터 부족)</p>';
                      }}
                    />
                  </div>
                ) : (
                  <p className="muted">정서 리뷰가 부족합니다.</p>
                )}
              </div>
              <div className="taste-preview-side">
                <p className="muted">관심 키워드</p>
                {wordCloudLoading ? (
                  <p className="muted">불러오는 중...</p>
                ) : wordCloudError ? (
                  <p className="muted">{wordCloudError}</p>
                ) : wordCloudUrl ? (
                  <div className="word-cloud-image-container" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", padding: "16px" }}>
                    <img
                      src={wordCloudUrl}
                      alt="관심 키워드 워드 클라우드"
                      style={{ width: "100%", maxWidth: "500px", height: "auto", borderRadius: "8px", objectFit: "contain" }}
                      onError={(e) => {
                        (e.target as HTMLImageElement).style.display = 'none';
                        (e.target as HTMLImageElement).parentElement!.innerHTML = '<p class="muted">키워드를 불러올 수 없습니다.<br/>(데이터 부족)</p>';
                      }}
                    />
                  </div>
                ) : computedWordCloudUrl ? (
                  <div className="word-cloud-image-container" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", padding: "16px" }}>
                    <img
                      src={computedWordCloudUrl.replace("type=both", "type=boost")}
                      alt="관심 키워드 워드 클라우드"
                      style={{ width: "100%", maxWidth: "500px", height: "auto", borderRadius: "8px", objectFit: "contain" }}
                      onError={(e) => {
                        (e.target as HTMLImageElement).style.display = 'none';
                        (e.target as HTMLImageElement).parentElement!.innerHTML = '<p class="muted">키워드를 불러올 수 없습니다.<br/>(데이터 부족)</p>';
                      }}
                    />
                  </div>
                ) : (
                  <p className="muted">데이터 추출 중입니다.</p>
                )}
              </div>
            </div>
          </article>
        </section>

        <section className="section card taste-preview-section">
          <article className="taste-preview">
            <div className="taste-preview-header">
              <h2>장르 선호도</h2>
              <p>가장 선호하는 장르 5개</p>
            </div>
            <div className="taste-preview-body">
              <div className="genre-card-grid">
                {preferenceSlots.map((item, index) => (
                  <div
                    key={`${item.genre}-${index}`}
                    className={`genre-card ${item.percent === 0 ? "is-empty" : ""}`}
                  >
                    <span className="genre-card-title">{item.genre}</span>
                    <div
                      className="genre-card-meter"
                      role="img"
                      aria-label={`선호도 ${item.percent}%`}
                      style={getFillStyle(item.percent)}
                    >
                      <span className="genre-card-icon" aria-hidden="true" />
                    </div>
                    <span className="genre-card-percent">{item.percent}%</span>
                  </div>
                ))}
              </div>
            </div>
          </article>
        </section>

        <section className="section">
          <SectionHeader
            title="최근 가장 만족했던 영화"
            description="최근 리뷰 중에서 4.5점 이상으로 평점을 저장했던 영화 4개를 보여줄게요"
          />
          {reviewsLoading ? (
            <LoadingState message="불러오는 중..." />
          ) : recentHighRated.length > 0 ? (
            <div className="movie-grid">
              {recentHighRated.map((movie) => (
                <Link
                  className="card-link"
                  to={`/movies/${movie.movieId}`}
                  key={movie.movieId}
                >
                  <MovieTileCard title={movie.title} posterUrl={movie.poster} />
                </Link>
              ))}
            </div>
          ) : (
            <EmptyState
              message={
                isLoggedIn
                  ? "조건에 맞는 최근 리뷰가 없습니다."
                  : "로그인 후 확인할 수 있어요."
              }
            />
          )}
        </section>
      </main>
      {isSurveyOpen && (
        <TasteSurveyModal
          onClose={handleSurveyClose}
          onComplete={handleSurveyComplete}
          initialData={surveyData || undefined}
        />
      )}
    </MainLayout>
  );
}





