import { useEffect, useState } from "react";
import MainLayout from "../components/layout/MainLayout";
import SectionHeader from "../components/common/SectionHeader";
import MovieTileCard from "../components/movie/MovieTileCard";
import LoadingState from "../components/common/LoadingState";
import { Link, useNavigate } from "react-router-dom";
import { getQuickRecommendations, type PersonalizedMovie } from "../api/personalized";
import TasteSurveyModal from "../components/TasteSurveyModal";
import { getAccessToken } from "../api/http";

const RECOMMENDED_PAGE_SIZE = 4;

const FAQ_ITEMS = [
  {
    q: "볼래! 말래?는 어떤 서비스인가요?",
    a: "취향 데이터를 바탕으로 영화 추천과 탐색을 쉽게 도와주는 서비스입니다.",
  },
  {
    q: "대화 추천은 어떤 기준으로 나오나요?",
    a: "대화에 포함된 키워드와 감성 태그를 분석해 유사한 분위기의 작품을 추천해요.",
  },
  {
    q: "다함께 추천은 어떻게 이용하나요?",
    a: "멤버를 선택하면 모두의 취향을 고려해 만족도가 높은 영화를 보여줘요.",
  },
  {
    q: "취향 설정은 언제 필요한가요?",
    a: "개인화 추천과 매칭 점수를 정확히 보려면 취향 설정이 필요합니다.",
  },
  {
    q: "영화 데이터는 어떻게 업데이트되나요?",
    a: "최신 인기작과 평점 데이터를 기준으로 정기 업데이트하고 있어요.",
  },
];

export default function HomePage() {
  const [openFaq, setOpenFaq] = useState<number | null>(null);
  const [recommendedMovies, setRecommendedMovies] = useState<PersonalizedMovie[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [recommendedPage, setRecommendedPage] = useState(1);
  const [needsTasteSetup, setNeedsTasteSetup] = useState(false);
  const [showTasteSurveyModal, setShowTasteSurveyModal] = useState(false);
  const navigate = useNavigate();

  const isLoggedIn = Boolean(getAccessToken());

  const fetchRecommendations = async () => {
    setLoading(true);
    try {
      // 백엔드에서 모든 계산 완료된 추천 가져오기
      const response = await getQuickRecommendations();
      setRecommendedMovies(response.recommendations);
      setNeedsTasteSetup(false);
    } catch (err: any) {
      console.error("Failed to fetch recommendations:", err);
      
      // 404 에러 = 취향 설정 필요
      if (err?.response?.status === 404) {
        setNeedsTasteSetup(true);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!isLoggedIn) return;
    void fetchRecommendations();
  }, [isLoggedIn]);

  useEffect(() => {
    setRecommendedPage(1);
  }, [recommendedMovies.length]);

  const handleSearch = () => {
    const trimmedQuery = searchQuery.trim();
    if (!trimmedQuery) return;
    navigate(`/llm-recommend?q=${encodeURIComponent(trimmedQuery)}`);
  };

  const recommendedTotalPages = Math.max(
    1,
    Math.ceil(recommendedMovies.length / RECOMMENDED_PAGE_SIZE)
  );
  const safeRecommendedPage = Math.min(recommendedPage, recommendedTotalPages);
  const recommendedSliceStart = (safeRecommendedPage - 1) * RECOMMENDED_PAGE_SIZE;
  const visibleRecommended = recommendedMovies.slice(
    recommendedSliceStart,
    recommendedSliceStart + RECOMMENDED_PAGE_SIZE
  );

  return (
    <MainLayout>
      <main className={`container ${isLoggedIn ? "home-page" : "landing-page"}`}>
        {!isLoggedIn ? (
          <>
            <section className="landing-hero">
              <div className="landing-hero-text">
                <span className="landing-badge">See or Not</span>
                <h1>오늘의 취향, 한 번에 찾아보기</h1>
                <p>
                  대화로 추천 받고, 마음에 들면 바로 탐색하세요. 간단하지만 확실한 추천
                  흐름을 제공합니다.
                </p>
              </div>
              <div className="landing-hero-side">
                <div className="landing-hero-panel">
                  <div className="panel-card">
                    <p className="panel-title">간편한 추천 루틴</p>
                    <p className="panel-desc">대화 → 후보 선택 → 바로 감상</p>
                  </div>
                  <div className="panel-card">
                    <p className="panel-title">취향 조합</p>
                    <p className="panel-desc">장르, 길이, 분위기까지 조합해서 추천</p>
                  </div>
                </div>
                <div className="landing-actions" />
              </div>
            </section>

            <section className="landing-grid">
              <article className="landing-card">
                <h2>대화형 추천</h2>
                <p>지금 기분이나 보고 싶은 분위기를 말해보세요.</p>
              </article>
              <article className="landing-card">
                <h2>취향 기반 탐색</h2>
                <p>선호 장르, 길이, 분위기를 쉽게 조합할 수 있어요.</p>
              </article>
              <article className="landing-card">
                <h2>다함께 추천</h2>
                <p>모임 멤버들의 취향을 모아 모두 만족하는 영화를 찾습니다.</p>
              </article>
            </section>

            <section className="landing-strip">
              <div className="strip-head">
                <h2>이런 흐름으로 추천돼요</h2>
                <p>복잡하지 않고 직관적인 단계로 구성했어요.</p>
              </div>
              <div className="strip-steps">
                <div className="strip-step">
                  <span>01</span>
                  <p>간단한 대화로 취향 파악</p>
                </div>
                <div className="strip-step">
                  <span>02</span>
                  <p>조건을 합쳐 추천 후보 생성</p>
                </div>
                <div className="strip-step">
                  <span>03</span>
                  <p>바로 감상할 영화 선택</p>
                </div>
              </div>
            </section>

            <section className="landing-faq">
              <div className="landing-faq-inner">
                <div className="landing-faq-header">
                  <h2>자주 묻는 질문</h2>
                  <p>가장 많이 찾는 질문들을 모아두었어요.</p>
                </div>
                <div className="landing-faq-list">
                  {FAQ_ITEMS.map((item, index) => {
                    const isOpen = openFaq === index;
                    return (
                      <div
                        className={`landing-faq-item ${isOpen ? "is-open" : ""}`}
                        key={item.q}
                      >
                        <button
                          type="button"
                          className="landing-faq-question"
                          onClick={() => setOpenFaq(isOpen ? null : index)}
                          aria-expanded={isOpen}
                        >
                          <span>{item.q}</span>
                          <span className="faq-plus">{isOpen ? "−" : "+"}</span>
                        </button>
                        {isOpen && <div className="landing-faq-answer">{item.a}</div>}
                      </div>
                    );
                  })}
                </div>
                <Link className="ghost-btn landing-faq-link" to="/support">
                  고객센터 바로가기
                </Link>
              </div>
            </section>
          </>
        ) : (
          <>
            <section className="landing-hero">
              <div className="landing-hero-text">
                <span className="landing-badge">See or Not</span>
                <h1>오늘의 취향, 한 번에 찾아보기</h1>
                <p>
                  대화로 추천 받고, 마음에 들면 바로 탐색하세요. 간단하지만 확실한 추천
                  흐름을 제공합니다.
                </p>
              </div>
              <div className="landing-hero-side">
                <div className="landing-hero-panel">
                  <div className="panel-card">
                    <p className="panel-title">간편한 추천 루틴</p>
                    <p className="panel-desc">대화 → 후보 선택 → 바로 감상</p>
                  </div>
                  <div className="panel-card">
                    <p className="panel-title">취향 조합</p>
                    <p className="panel-desc">장르, 길이, 분위기까지 조합해서 추천</p>
                  </div>
                </div>
                <div className="landing-actions" />
              </div>
              <div className="landing-hero-search">
                <input
                  className="search-input"
                  type="text"
                  placeholder="'감동적인 영화 추천해줘' 같은 자연어로 검색해보세요"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                />
                <button className="primary-btn" type="button" onClick={handleSearch}>
                  맞춤 추천 받기
                </button>
              </div>
            </section>

            <section className="section">
              <SectionHeader
                title="나를 위한 추천"
                actions={
                  <div className="home-recommend-controls">
                    <button
                      className="icon-btn page-arrow-btn"
                      type="button"
                      aria-label="이전 페이지"
                      onClick={() => setRecommendedPage((prev) => Math.max(1, prev - 1))}
                      disabled={safeRecommendedPage === 1}
                    >
                      {"◀"}
                    </button>
                    <span className="page-number-text" aria-live="polite">
                      {safeRecommendedPage}/{recommendedTotalPages}
                    </span>
                    <button
                      className="icon-btn page-arrow-btn"
                      type="button"
                      aria-label="다음 페이지"
                      onClick={() => setRecommendedPage((prev) => Math.min(recommendedTotalPages, prev + 1))}
                      disabled={safeRecommendedPage >= recommendedTotalPages}
                    >
                      {"▶"}
                    </button>
                  </div>
                }
              />

              {needsTasteSetup ? (
                <div
                  style={{
                    textAlign: "center",
                    padding: "1rem 0",
                    margin: "1rem 0",
                  }}
                >
                  <p style={{ fontSize: "1.2rem", marginBottom: "0.75rem", color: "var(--text)" }}>
                    취향 설정이 필요합니다
                  </p>
                  <p style={{ fontSize: "1rem", marginBottom: "1rem", color: "var(--text)" }}>
                    나만의 맞춤 추천을 받으려면 취향을 설정해주세요.
                  </p>
                  <button className="primary-btn" onClick={() => setShowTasteSurveyModal(true)}>
                    취향 설정하기
                  </button>
                </div>
              ) : (
                <>
                  {loading && <LoadingState />}

                  {!loading && recommendedMovies.length > 0 && (
                    <div className="movie-grid">
                      {visibleRecommended.map((movie) => (
                        <Link className="card-link" to={`/movies/${movie.movie_id}`} key={movie.movie_id}>
                          <MovieTileCard
                            title={movie.title}
                            posterUrl={
                              movie.poster_url ||
                              "https://via.placeholder.com/500x750?text=No+Image"
                            }
                          >
                            <p className="probability home-match-probability">
                              적합 확률 {movie.match_rate}%
                            </p>
                            <p className="muted synopsis-clamp">
                              {movie.synopsis
                                ? movie.synopsis.substring(0, 60) +
                                  (movie.synopsis.length > 60 ? "..." : "")
                                : "줄거리 정보가 없습니다."}
                            </p>
                          </MovieTileCard>
                        </Link>
                      ))}
                    </div>
                  )}
                </>
              )}
            </section>
          </>
        )}
        {showTasteSurveyModal && (
          <TasteSurveyModal
            onClose={() => setShowTasteSurveyModal(false)}
            onComplete={() => {
              setShowTasteSurveyModal(false);
              setNeedsTasteSetup(false);
              void fetchRecommendations();
            }}
          />
        )}
      </main>
    </MainLayout>
  );
}
