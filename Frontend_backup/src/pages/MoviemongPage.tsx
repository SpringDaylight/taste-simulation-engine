import {
  useEffect,
  useRef,
  useState,
  type PointerEvent as ReactPointerEvent,
} from "react";
import MainLayout from "../components/layout/MainLayout";
import "../components/roulette/roulette.css";
import moviemongLv1 from "../assets/monkeymong-lv1.png";
import moviemongTheme1 from "../assets/moviemong-theme1.png";
import moviemongTheme2 from "../assets/moviemong-theme2.png";
import moviemongTheme3 from "../assets/moviemong-theme3.png";
import moviemongTheme4 from "../assets/moviemong-theme4.png";
import Roulette from "../components/roulette/Roulette";
import { rouletteItems, type RouletteItem } from "../components/roulette/rouletteItems";
import { getCurrentUser } from "../api/A7_profile";
import { getRouletteConfig, getRouletteStatus, spinRoulette } from "../api/A9_roulette";
import { getAccessToken } from "../api/http";
type QuestionItem = {
  id: number;
  question: string;
  createdAt: string;
  answer: string;
};

type MoviemongThemeItem = {
  id: string;
  imageSrc: string;
  alt: string;
};

type TabType = "question" | "feed" | "theme" | "recipe" | "bag";

const QUESTION_PAGE_SIZE = 10;
const questionItems: QuestionItem[] = Array.from({ length: 32 }, (_, index) => {
  const day = String((index % 28) + 1).padStart(2, "0");
  return {
    id: index + 1,
    question: `질문 내용 ${index + 1}번입니다.`,
    createdAt: `2026-02-${day}`,
    answer: `답변 내용 ${index + 1}번입니다.`,
  };
});

const moviemongThemeItems: MoviemongThemeItem[] = [
  { id: "theme-1", imageSrc: moviemongTheme1, alt: "무비몽 테마 1" },
  { id: "theme-2", imageSrc: moviemongTheme2, alt: "무비몽 테마 2" },
  { id: "theme-3", imageSrc: moviemongTheme3, alt: "무비몽 테마 3" },
  { id: "theme-4", imageSrc: moviemongTheme4, alt: "무비몽 테마 4" },
];

export default function MoviemongPage() {
  const getNextExpRequirement = (nextLevel: number) => {
    if (nextLevel <= 1) return 0;
    if (nextLevel <= 5) return 50 * (nextLevel - 1);
    if (nextLevel <= 10) return 300 + 50 * (nextLevel - 6);
    if (nextLevel <= 15) return 500 + 60 * (nextLevel - 10);
    if (nextLevel <= 20) return 800 + 40 * (nextLevel - 15);
    if (nextLevel <= 25) return 1000 + 100 * (nextLevel - 20);
    if (nextLevel <= 30) return 1500 + 100 * (nextLevel - 25);
    return 2000;
  };

  const deriveLevelFromTotalExp = (totalExp: number) => {
    let levelValue = 1;
    let remainingExp = Number.isFinite(totalExp) ? totalExp : 0;
    if (remainingExp < 0) remainingExp = 0;

    while (true) {
      const nextRequirement = getNextExpRequirement(levelValue + 1);
      if (nextRequirement <= 0) break;
      if (remainingExp >= nextRequirement) {
        remainingExp -= nextRequirement;
        levelValue += 1;
        continue;
      }
      break;
    }

    return { level: levelValue, expValue: remainingExp };
  };

  const [activeTab, setActiveTab] = useState<TabType | null>(null);
  const [panelVersion, setPanelVersion] = useState(0);
  const [level, setLevel] = useState(1);
  const [popcornCount, setPopcornCount] = useState(0);
  const [expValue, setExpValue] = useState(0);
  const [questionPage, setQuestionPage] = useState(1);
  const [expandedQuestionId, setExpandedQuestionId] = useState<number | null>(
    null
  );
  const [questionQuery, setQuestionQuery] = useState("");
  const [selectedThemeId, setSelectedThemeId] = useState<string | null>("theme-1");
  const [canThemeScrollLeft, setCanThemeScrollLeft] = useState(false);
  const [canThemeScrollRight, setCanThemeScrollRight] = useState(false);
  const [isThemeDragging, setIsThemeDragging] = useState(false);
  const [rouletteWheelItems, setRouletteWheelItems] = useState<RouletteItem[]>(
    rouletteItems
  );
  const [pendingReward, setPendingReward] = useState<{
    totalPopcorn: number;
    totalExp: number;
  } | null>(null);
  const themeScrollRef = useRef<HTMLDivElement | null>(null);
  const themeDragRef = useRef<{
    pointerId: number;
    startX: number;
    startScrollLeft: number;
    themeId: string | null;
  } | null>(null);
  const themeDragMovedRef = useRef(false);
  const isLoggedIn = Boolean(getAccessToken());
  const selectedTheme = moviemongThemeItems.find(
    (theme) => theme.id === selectedThemeId
  );
  const heroThemeBackgroundStyle =
    selectedTheme && isLoggedIn
      ? {
          backgroundImage: `url(${selectedTheme.imageSrc})`,
        }
      : undefined;
  const expMax = getNextExpRequirement(level + 1);
  const expPercent =
    expMax > 0 ? Math.min(100, Math.round((expValue / expMax) * 100)) : 0;
  const normalizedQuery = questionQuery.trim().toLowerCase();
  const filteredQuestions = questionItems.filter((item) => {
    if (!normalizedQuery) return true;
    return (
      item.question.toLowerCase().includes(normalizedQuery) ||
      item.answer.toLowerCase().includes(normalizedQuery)
    );
  });
  const totalQuestionPages = Math.max(
    1,
    Math.ceil(filteredQuestions.length / QUESTION_PAGE_SIZE)
  );
  const safeQuestionPage = Math.min(questionPage, totalQuestionPages);
  const pagedQuestions = filteredQuestions.slice(
    (safeQuestionPage - 1) * QUESTION_PAGE_SIZE,
    safeQuestionPage * QUESTION_PAGE_SIZE
  );
  const hasQuestions = filteredQuestions.length > 0;
  const rangeStart = hasQuestions
    ? (safeQuestionPage - 1) * QUESTION_PAGE_SIZE + 1
    : 0;
  const rangeEnd = hasQuestions
    ? Math.min(safeQuestionPage * QUESTION_PAGE_SIZE, filteredQuestions.length)
    : 0;

  const handleRouletteSpin = async (): Promise<RouletteItem | null> => {
    if (!isLoggedIn) {
      alert("로그인 후 이용해주세요.");
      return null;
    }
    try {
      const status = await getRouletteStatus();
      if (!status.can_spin) {
        alert("이미 룰렛을 사용했어요.");
        return null;
      }

      const response = await spinRoulette();
      const matched = rouletteWheelItems.find(
        (item) => item.label === response.item
      );
      const resultItem: RouletteItem = matched
        ? {
            ...matched,
            popcornGain: response.popcorn_gain ?? matched.popcornGain,
            expGain: response.exp_gain ?? matched.expGain,
          }
        : {
            label: response.item,
            probability: "",
            popcornGain: response.popcorn_gain ?? 0,
            expGain: response.exp_gain ?? 0,
          };

      setPendingReward({
        totalPopcorn: response.total_popcorn,
        totalExp: response.total_exp,
      });
      return resultItem;
    } catch (error) {
      console.error("Failed to spin roulette:", error);
      const message = error instanceof Error ? error.message : "룰렛 결과를 불러오지 못했습니다.";
      alert(message || "룰렛 결과를 불러오지 못했습니다.");
      return null;
    }
  };

  const refreshTabSection = (tab: TabType) => {
    if (tab === "question") {
      setQuestionPage(1);
      setExpandedQuestionId(null);
      setQuestionQuery("");
    }
  };

  const handleTabClick = (tab: TabType) => {
    if (activeTab === tab) {
      refreshTabSection(tab);
      setPanelVersion((prev) => prev + 1);
      return;
    }
    setActiveTab(tab);
    setPanelVersion((prev) => prev + 1);
  };

  const updateThemeScrollState = () => {
    const scrollEl = themeScrollRef.current;
    if (!scrollEl) {
      setCanThemeScrollLeft(false);
      setCanThemeScrollRight(false);
      return;
    }
    const maxScrollLeft = scrollEl.scrollWidth - scrollEl.clientWidth;
    setCanThemeScrollLeft(scrollEl.scrollLeft > 1);
    setCanThemeScrollRight(maxScrollLeft - scrollEl.scrollLeft > 1);
  };

  useEffect(() => {
    if (activeTab !== "theme") {
      setCanThemeScrollLeft(false);
      setCanThemeScrollRight(false);
      setIsThemeDragging(false);
      themeDragRef.current = null;
      return;
    }

    const scrollEl = themeScrollRef.current;
    if (!scrollEl) return;

    updateThemeScrollState();

    const handleScroll = () => updateThemeScrollState();
    const handleResize = () => updateThemeScrollState();
    scrollEl.addEventListener("scroll", handleScroll, { passive: true });
    window.addEventListener("resize", handleResize);

    let resizeObserver: ResizeObserver | null = null;
    if (typeof ResizeObserver !== "undefined") {
      resizeObserver = new ResizeObserver(() => updateThemeScrollState());
      resizeObserver.observe(scrollEl);
    }

    return () => {
      scrollEl.removeEventListener("scroll", handleScroll);
      window.removeEventListener("resize", handleResize);
      resizeObserver?.disconnect();
    };
  }, [activeTab, panelVersion]);

  const handleThemeScrollPrev = () => {
    const scrollEl = themeScrollRef.current;
    if (!scrollEl) return;
    const prevStep = Math.max(180, Math.round(scrollEl.clientWidth * 0.72));
    scrollEl.scrollBy({ left: -prevStep, behavior: "smooth" });
  };

  const handleThemeScrollNext = () => {
    const scrollEl = themeScrollRef.current;
    if (!scrollEl) return;
    const nextStep = Math.max(180, Math.round(scrollEl.clientWidth * 0.72));
    scrollEl.scrollBy({ left: nextStep, behavior: "smooth" });
  };

  const handleThemePointerDown = (
    event: ReactPointerEvent<HTMLDivElement>
  ) => {
    if (event.pointerType !== "mouse") return;
    const scrollEl = themeScrollRef.current;
    if (!scrollEl) return;
    const target = event.target as HTMLElement;
    const themeCard = target.closest<HTMLElement>(".moviemong-theme-card");
    const themeId = themeCard?.dataset.themeId ?? null;

    themeDragMovedRef.current = false;
    themeDragRef.current = {
      pointerId: event.pointerId,
      startX: event.clientX,
      startScrollLeft: scrollEl.scrollLeft,
      themeId,
    };
    setIsThemeDragging(true);
    scrollEl.setPointerCapture(event.pointerId);
  };

  const handleThemePointerMove = (
    event: ReactPointerEvent<HTMLDivElement>
  ) => {
    const scrollEl = themeScrollRef.current;
    const dragState = themeDragRef.current;
    if (!scrollEl || !dragState || dragState.pointerId !== event.pointerId) return;

    const deltaX = event.clientX - dragState.startX;
    if (Math.abs(deltaX) > 6) {
      themeDragMovedRef.current = true;
    }
    scrollEl.scrollLeft = dragState.startScrollLeft - deltaX;
  };

  const handleThemePointerEnd = (
    event: ReactPointerEvent<HTMLDivElement>
  ) => {
    const scrollEl = themeScrollRef.current;
    const dragState = themeDragRef.current;
    if (!scrollEl || !dragState || dragState.pointerId !== event.pointerId) return;
    const shouldSelectTheme =
      !themeDragMovedRef.current && Boolean(dragState.themeId);

    if (scrollEl.hasPointerCapture(event.pointerId)) {
      scrollEl.releasePointerCapture(event.pointerId);
    }
    themeDragRef.current = null;
    setIsThemeDragging(false);
    updateThemeScrollState();
    if (shouldSelectTheme && dragState.themeId) {
      setSelectedThemeId(dragState.themeId);
    }
    themeDragMovedRef.current = false;
  };

    const handleThemeSelect = (themeId: string) => {
    if (themeDragMovedRef.current) {
      themeDragMovedRef.current = false;
      return;
    }
    setSelectedThemeId(themeId);
  };

  const handleRouletteConfirm = () => {
    if (!pendingReward) return;
    setPopcornCount(pendingReward.totalPopcorn);
    const { level: nextLevel, expValue: nextExpValue } =
      deriveLevelFromTotalExp(pendingReward.totalExp);
    setLevel(nextLevel);
    setExpValue(nextExpValue);
    setPendingReward(null);
  };

  useEffect(() => {
    let isCancelled = false;

    const loadRouletteConfig = async () => {
      try {
        const config = await getRouletteConfig();
        if (isCancelled) return;
        if (Array.isArray(config.items) && config.items.length > 0) {
          const mapped: RouletteItem[] = config.items.map((item) => ({
            label: item.label,
            probability: item.probability,
            popcornGain: item.popcorn_gain,
            expGain: item.exp_gain,
          }));
          setRouletteWheelItems(mapped);
        }
      } catch (error) {
        console.error("Failed to load roulette config:", error);
        if (!isCancelled) {
          setRouletteWheelItems(rouletteItems);
        }
      }
    };

    loadRouletteConfig();

    return () => {
      isCancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!isLoggedIn) {
      setLevel(1);
      setExpValue(0);
      setPopcornCount(0);
      return;
    }

    let isCancelled = false;

    const loadUserStats = async () => {
      try {
        const user = await getCurrentUser();
        if (isCancelled) return;
        const totalExp = typeof user.exp === "number" ? user.exp : 0;
        const { level: nextLevel, expValue: nextExpValue } =
          deriveLevelFromTotalExp(totalExp);
        setLevel(nextLevel);
        setExpValue(nextExpValue);
        setPopcornCount(typeof user.popcorn === "number" ? user.popcorn : 0);
      } catch (error) {
        console.error("Failed to load moviemong stats:", error);
        setLevel(1);
        setExpValue(0);
        setPopcornCount(0);
      }
    };

    loadUserStats();

    return () => {
      isCancelled = true;
    };
    }, [isLoggedIn]);

  return (
    <MainLayout>
      <main className="container reviewmong-page">
        <section className="section">
          <div
            className={`reviewmong-hero ${selectedTheme ? "has-theme-bg" : ""}`}
            style={heroThemeBackgroundStyle}
          >
            {isLoggedIn ? (
              <>
                <div className="reviewmong-stats">
                  <span>레벨 {level}</span>
                  <span>팝콘 {popcornCount}</span>
                </div>
                <div className="reviewmong-hero-content">
                  <img src={moviemongLv1} alt="Moviemong preview" />
                  <div className="reviewmong-exp">
                    <div className="reviewmong-exp-header">
                      <span>EXP</span>
                      <span>
                        {expValue}/{expMax}
                      </span>
                    </div>
                    <div className="reviewmong-exp-bar">
                      <span style={{ width: `${expPercent}%` }} />
                    </div>
                  </div>
                </div>
              </>
            ) : (
              <div className="reviewmong-login-placeholder">
                {/* <h2>무비몽</h2> */}
                <p className="muted login-required-text">로그인 후 이용해주세요.</p>
              </div>
            )}
          </div>
        </section>
        <section>
          <div className="reviewmong-actions">
            <button
              className={`secondary-btn ${activeTab === "question" ? "is-active" : ""}`}
              type="button"
              onClick={() => handleTabClick("question")}
            >
              질문
            </button>
            <button
              className={`secondary-btn ${activeTab === "feed" ? "is-active" : ""}`}
              type="button"
              onClick={() => handleTabClick("feed")}
            >
              룰렛
            </button>
            <button
              className={`secondary-btn ${activeTab === "theme" ? "is-active" : ""}`}
              type="button"
              onClick={() => handleTabClick("theme")}
            >
              <p className="question-title">테마</p>
            </button>
            <button
              className={`secondary-btn ${activeTab === "recipe" ? "is-active" : ""}`}
              type="button"
              onClick={() => handleTabClick("recipe")}
            >
              <p className="question-title">취향 레시피</p>
            </button>
            <button
              className={`secondary-btn ${activeTab === "bag" ? "is-active" : ""}`}
              type="button"
              onClick={() => handleTabClick("bag")}
            >
              <p className="question-title">보관함</p>
            </button>
          </div>
            <div
            key={`reviewmong-panel-${activeTab}-${panelVersion}`}
            className={`reviewmong-panel ${activeTab === null ? "is-hidden" : ""}`}
          >
            {!isLoggedIn ? (
              <div className="reviewmong-login-placeholder">
                <p className="muted login-required-text">로그인 후 이용해주세요.</p>
              </div>
            ) : (
              <>
                {activeTab === "question" && (
                  <div className="reviewmong-question">
                    <p className="question-title">오늘의 질문</p>
                    <p className="question-text">
                      Q1. 최근에 영화관에서 본 영화는 무엇인가요?
                    </p>
                    <textarea
                      className="question-input"
                      placeholder="답변을 입력해 주세요. (250bytes)"
                      maxLength={250}
                    />
                    <div className="question-actions">
                      <button className="primary-btn question-submit-btn" type="button">
                        답변하기
                      </button>
                    </div>
                    <div className="question-history">
                      <div className="question-history-header">
                        <span>이전 질문 목록</span>
                        <span>
                          {filteredQuestions.length}개 중 {rangeStart}-{rangeEnd}개
                        </span>
                      </div>
                      <div className="question-list">
                        {pagedQuestions.map((item) => {
                          const isOpen = expandedQuestionId === item.id;
                          return (
                            <div className="question-item" key={item.id}>
                              <button
                                className="question-item-header"
                                type="button"
                                onClick={() =>
                                  setExpandedQuestionId((prev) =>
                                    prev === item.id ? null : item.id
                                  )
                                }
                              >
                                <span className="question-item-number">Q{item.id}.</span>
                                <span className="question-item-text">{item.question}</span>
                                <span className="question-item-date">{item.createdAt}</span>
                              </button>
                              {isOpen && (
                                <div className="question-item-answer">
                                  <span className="question-item-answer-label">답변</span>
                                  <p>{item.answer}</p>
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                      {totalQuestionPages > 1 && (
                        <div className="question-pagination">
                          <button
                            type="button"
                            className="secondary-btn"
                            onClick={() =>
                              setQuestionPage((prev) => Math.max(1, prev - 1))
                            }
                            disabled={safeQuestionPage === 1}
                          >
                            이전
                          </button>
                          {Array.from(
                            { length: totalQuestionPages },
                            (_, index) => index + 1
                          ).map((page) => (
                            <button
                              key={page}
                              type="button"
                              className={`secondary-btn ${
                                page === safeQuestionPage ? "is-active" : ""
                              }`}
                              onClick={() => setQuestionPage(page)}
                            >
                              {page}
                            </button>
                          ))}
                          <button
                            type="button"
                            className="secondary-btn"
                            onClick={() =>
                              setQuestionPage((prev) =>
                                Math.min(totalQuestionPages, prev + 1)
                              )
                            }
                            disabled={safeQuestionPage === totalQuestionPages}
                          >
                            다음
                          </button>
                        </div>
                      )}
                      <div className="question-search">
                        <input
                          type="text"
                          value={questionQuery}
                          onChange={(event) => {
                            setQuestionQuery(event.target.value);
                            setQuestionPage(1);
                          }}
                          placeholder="질문/답변 검색"
                        />
                        <button
                          type="button"
                          className="primary-btn question-search-btn"
                          onClick={() => setQuestionPage(1)}
                        >
                          검색
                        </button>
                      </div>
                    </div>
                  </div>
                )}
                {activeTab === "feed" && (
                  <Roulette
                    items={rouletteWheelItems}
                    onSpin={handleRouletteSpin}
                    onResultConfirm={handleRouletteConfirm}
                  />
                )}
                {activeTab === "theme" && (
                  <div className="reviewmong-question">
              <p className="question-title">테마</p>
                    <p className="question-text">무비몽 테마를 골라보세요.</p>
                    <div className="reviewmong-theme-wrap">
                      {canThemeScrollLeft && (
                        <button
                          type="button"
                          className="reviewmong-theme-prev-btn"
                          aria-label="이전 테마 보기"
                          onClick={handleThemeScrollPrev}
                        >
                          ◀
                        </button>
                      )}
                      <div
                        className={`reviewmong-theme-scroll ${
                          isThemeDragging ? "is-dragging" : ""
                        }`}
                        ref={themeScrollRef}
                        onPointerDown={handleThemePointerDown}
                        onPointerMove={handleThemePointerMove}
                        onPointerUp={handleThemePointerEnd}
                        onPointerCancel={handleThemePointerEnd}
                      >
                        {moviemongThemeItems.map((theme) => (
                          <button
                            key={theme.id}
                            type="button"
                            className={`moviemong-theme-card ${
                              selectedThemeId === theme.id ? "is-selected" : ""
                            }`}
                            data-theme-id={theme.id}
                            aria-pressed={selectedThemeId === theme.id}
                            onClick={() => handleThemeSelect(theme.id)}
                          >
                            <img
                              src={theme.imageSrc}
                              alt={theme.alt}
                              loading="lazy"
                              draggable={false}
                            />
                            {selectedThemeId === theme.id && (
                              <span className="moviemong-theme-check" aria-hidden="true">
                                {"\u2713"}
                              </span>
                            )}
                          </button>
                        ))}
                      </div>
                      {canThemeScrollRight && (
                        <button
                          type="button"
                          className="reviewmong-theme-next-btn"
                          aria-label="다음 테마 보기"
                          onClick={handleThemeScrollNext}
                        >
                          ▶
                        </button>
                      )}
                    </div>
                  </div>
                )}
                {/* {activeTab === "recipe" && (
                  <div className="reviewmong-question">
              <p className="question-title">취향 레시피</p>
                    <p className="question-text">준비중이에요.</p>
                  </div>
                )} */}
                {activeTab === "bag" && (
                  <div className="reviewmong-question">
              <p className="question-title">보관함</p>
                    <p className="question-text">준비중이에요.</p>
                  </div>
                )}
              </>
            )}
          </div>
        </section>
      </main>
    </MainLayout>
  );
}




