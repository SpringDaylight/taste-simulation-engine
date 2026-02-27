import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import MainLayout from "../components/layout/MainLayout";
import ticketIcon from "../assets/icon-ticket-ver2.png";
import { getMovie } from "../api/A2_movies";
import { changePassword } from "../api/auth";
// import { getKakaoLoginUrl } from "../api/auth";
import {
  deleteCurrentUser,
  getCurrentUser,
  getCurrentUserReviews,
  updateCurrentUser,
} from "../api/A7_profile";
import {
  deleteCurrentUserWatchedMovie,
  getCurrentUserWatchedMovies,
} from "../api/A8_watched";
import { getAccessToken, setAccessToken } from "../api/http";

type ViewMode = "posters" | "reviews";
type ProfileState = {
  nickname: string;
  realname: string;
  age: string;
  gender: string;
  id: string;
  email: string;
  bio: string;
};

type ReviewReply = {
  id: number;
  author: string;
  content: string;
  createdAt: string;
};

type ReviewVisibility = "public" | "private";

type ReviewItem = {
  id: number;
  movieId: number;
  title: string;
  poster: string;
  dateLabel: string;
  genre: string;
  rating: number;
  content: string;
  createdAt: string;
  visibility: ReviewVisibility;
  replies: ReviewReply[];
};

type WatchedMovieItem = {
  movieId: number;
  title: string;
  poster?: string | null;
  addedAt?: string;
  genres?: string[] | null;
};


const formatDateTime = (value?: string | null) => {
  const date = value ? new Date(value) : new Date();
  if (Number.isNaN(date.getTime())) return "날짜 정보 없음";
  return date.toLocaleString("ko-KR", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
};

const defaultProfile: ProfileState = {
  nickname: "닉네임",
  realname: "사용자",
  age: "선택 안함",
  gender: "선택 안함",
  id: "watched_01",
  email: "you@example.com",
  bio: "",
  // bio: "감정선 강한 드라마 · SF를 자주 봐요.",
};

const WATCHED_PAGE_SIZE = 30;
const REVIEWS_PAGE_SIZE = 12;

const normalizeLegacyProfileGender = (value: string | null): string | null => {
  if (!value) return value;
  if (value === "선택 안함" || value === "여성" || value === "남성") {
    return value;
  }
  return "선택 안함";
};
// 생년월일 기준 실제 나이 계산
const getAgeLabelFromBirthdate = (birthdate: string | null): string | null => {
  if (!birthdate) return null;

  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(birthdate.trim());
  if (!match) return null;

  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  if (!Number.isFinite(year) || !Number.isFinite(month) || !Number.isFinite(day)) {
    return null;
  }

  const now = new Date();
  let age = now.getFullYear() - year;
  const hasNotHadBirthdayThisYear =
    now.getMonth() + 1 < month ||
    (now.getMonth() + 1 === month && now.getDate() < day);
  if (hasNotHadBirthdayThisYear) age -= 1;
  if (age < 0 || age > 130) return null;

  return `만 ${age}세`;
};

export default function ActivityPage() {
  const [view, setView] = useState<ViewMode>("posters");
  const navigate = useNavigate();
  const [profile, setProfile] = useState<ProfileState>(defaultProfile);
  const [editDraft, setEditDraft] = useState<ProfileState>(defaultProfile);
  const [birthDate, setBirthDate] = useState<string | null>(null);
  const [currentUserId, setCurrentUserId] = useState<string | null>(null);
  const [editVisible, setEditVisible] = useState(false);
  const [passwordVisible, setPasswordVisible] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [savedReviews, setSavedReviews] = useState<ReviewItem[]>([]);
  const [savedWatchedMovies, setSavedWatchedMovies] = useState<WatchedMovieItem[]>([]);
  const [topWatchedGenres, setTopWatchedGenres] = useState<string[]>([]);
  const [watchedPage, setWatchedPage] = useState(1);
  const [reviewPage, setReviewPage] = useState(1);
  const [watchedSearch, setWatchedSearch] = useState("");
  const [appliedWatchedSearch, setAppliedWatchedSearch] = useState("");
  const [currentPassword, setCurrentPassword] = useState("");
  const [nextPassword, setNextPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [isPasswordSaving, setIsPasswordSaving] = useState(false);
  const [passwordSuccessVisible, setPasswordSuccessVisible] = useState(false);
  const [deleteConfirmVisible, setDeleteConfirmVisible] = useState(false);
  const [deleteSuccessVisible, setDeleteSuccessVisible] = useState(false);
  const [isDeletingAccount, setIsDeletingAccount] = useState(false);
  const [isGenderSelectOpen, setIsGenderSelectOpen] = useState(false);
  const pendingScrollTarget = useRef<string | null>(null);
  const genderSelectRef = useRef<HTMLDivElement | null>(null);
  // const isKakaoLinked = Boolean(localStorage.getItem("mw_access_token"));
  // const isGoogleLinked = Boolean(localStorage.getItem("mw_google_token"));
  const isLoggedIn = useMemo(() => Boolean(getAccessToken()), []);

  const posterItems = useMemo(
    () =>
      savedWatchedMovies.map((item) => ({
        id: item.movieId,
        movieId: item.movieId,
        to: `/movies/${item.movieId}`,
        src:
          item.poster ||
          "https://via.placeholder.com/500x750?text=No+Image",
        alt: `${item.title} 포스터`,
        title: item.title,
      })),
    [savedWatchedMovies]
  );
  const normalizedWatchedSearch = appliedWatchedSearch.trim().toLowerCase();
  const filteredPosterItems = useMemo(() => {
    if (!normalizedWatchedSearch) return posterItems;
    return posterItems.filter((item) =>
      item.title.toLowerCase().includes(normalizedWatchedSearch)
    );
  }, [posterItems, normalizedWatchedSearch]);
  const mergedReviewItems = useMemo(() => {
    const seen = new Set<number>();
    return savedReviews.filter((item) => {
      if (seen.has(item.id)) return false;
      seen.add(item.id);
      return true;
    });
  }, [savedReviews]);

  useEffect(() => {
    if (!isGenderSelectOpen) return;
    const handleOutsideClick = (event: MouseEvent) => {
      if (!(event.target instanceof Node)) return;
      if (genderSelectRef.current && !genderSelectRef.current.contains(event.target)) {
        setIsGenderSelectOpen(false);
      }
    };
    document.addEventListener("mousedown", handleOutsideClick);
    return () => {
      document.removeEventListener("mousedown", handleOutsideClick);
    };
  }, [isGenderSelectOpen]);
  const topGenreLabel =
    topWatchedGenres.length > 0
      ? topWatchedGenres.join(" · ")
      : "시청한 영화를 저장해주세요";

  const watchedTotalPages = Math.max(
    1,
    Math.ceil(filteredPosterItems.length / WATCHED_PAGE_SIZE)
  );
  const safeWatchedPage = Math.min(watchedPage, watchedTotalPages);
  const watchedSliceStart = (safeWatchedPage - 1) * WATCHED_PAGE_SIZE;
  const visiblePosters = filteredPosterItems.slice(
    watchedSliceStart,
    watchedSliceStart + WATCHED_PAGE_SIZE
  );
  const reviewTotalPages = Math.max(
    1,
    Math.ceil(mergedReviewItems.length / REVIEWS_PAGE_SIZE)
  );
  const safeReviewPage = Math.min(reviewPage, reviewTotalPages);
  const reviewSliceStart = (safeReviewPage - 1) * REVIEWS_PAGE_SIZE;
  const visibleReviews = mergedReviewItems.slice(
    reviewSliceStart,
    reviewSliceStart + REVIEWS_PAGE_SIZE
  );

  useEffect(() => {
    if (!isLoggedIn) {
      setProfile(defaultProfile);
      setEditDraft(defaultProfile);
      setBirthDate(null);
      return;
    }

    let isCancelled = false;

    const fetchProfile = async () => {
      try {
        const user = await getCurrentUser();
        if (isCancelled) return;

        const calculatedAge = getAgeLabelFromBirthdate(user.birth_date ?? null);
        const nextProfile: ProfileState = {
          nickname: user.nickname || user.name || defaultProfile.nickname,
          realname: user.name || defaultProfile.realname,
          age: calculatedAge || "나이 정보 없음",
          gender:
            normalizeLegacyProfileGender(user.gender ?? null) || defaultProfile.gender,
          id: user.user_id || user.id || defaultProfile.id,
          email: user.email || defaultProfile.email,
          bio: defaultProfile.bio,
        };

        setProfile(nextProfile);
        setEditDraft(nextProfile);
        setBirthDate(user.birth_date ?? null);
        setCurrentUserId(user.user_id ?? null);
      } catch (err) {
        console.error("Failed to load current user profile:", err);
        if (isCancelled) return;
        setProfile(defaultProfile);
        setEditDraft(defaultProfile);
        setBirthDate(null);
        setCurrentUserId(null);
      }
    };

    fetchProfile();

    return () => {
      isCancelled = true;
    };
  }, [isLoggedIn]);

  useEffect(() => {
    if (!isLoggedIn) {
      setSavedReviews([]);
      return;
    }

    let isCancelled = false;

    const fetchSavedReviews = async () => {
      try {
        const reviewResponse = await getCurrentUserReviews({
          page: 1,
          page_size: 100,
        });
        const normalizedReviews = await Promise.all(
          reviewResponse.reviews.map(async (review): Promise<ReviewItem> => {
            try {
              const movie = await getMovie(review.movie_id);
              return {
                id: review.id,
                movieId: review.movie_id,
                title: movie.title || `영화 #${review.movie_id}`,
                poster:
                  movie.poster_url ||
                  "https://via.placeholder.com/500x750?text=No+Image",
                dateLabel: formatDateTime(review.created_at),
                genre: movie.genres?.[0] ?? "장르",
                rating: Number(review.rating) || 0,
                content: review.content ?? "",
                createdAt: review.created_at,
                visibility: review.is_public === false ? "private" : "public",
                replies: [],
              };
            } catch (movieErr) {
              console.error(
                `Failed to fetch movie detail for movie_id=${review.movie_id}:`,
                movieErr
              );
              return {
                id: review.id,
                movieId: review.movie_id,
                title: `영화 #${review.movie_id}`,
                poster: "https://via.placeholder.com/500x750?text=No+Image",
                dateLabel: formatDateTime(review.created_at),
                genre: "장르",
                rating: Number(review.rating) || 0,
                content: review.content ?? "",
                createdAt: review.created_at,
                visibility: review.is_public === false ? "private" : "public",
                replies: [],
              };
            }
          })
        );

        if (isCancelled) return;
        normalizedReviews.sort(
          (a, b) =>
            new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
        );
        setSavedReviews(normalizedReviews);
      } catch (err) {
        if (isCancelled) return;
        console.error("Failed to fetch current user reviews:", err);
        setSavedReviews([]);
      }
    };

    fetchSavedReviews();

    return () => {
      isCancelled = true;
    };
  }, [isLoggedIn, profile.id]);

  useEffect(() => {
    if (!isLoggedIn) {
      setSavedWatchedMovies([]);
      setTopWatchedGenres([]);
      setWatchedPage(1);
      return;
    }

    let isCancelled = false;

    const fetchWatchedMovies = async () => {
      try {
        const response = await getCurrentUserWatchedMovies({
          page: 1,
          page_size: 100,
        });
        if (isCancelled) return;

        const normalizedApi = response.items.map((item) => ({
          movieId: Number(item.movie_id),
          title: item.title || `영화 #${item.movie_id}`,
          poster:
            item.poster_url ||
            "https://via.placeholder.com/500x750?text=No+Image",
          addedAt: item.watched_at || new Date().toISOString(),
          genres: null,
        }));

        const merged = normalizedApi.sort(
          (a, b) =>
            new Date(b.addedAt || 0).getTime() -
            new Date(a.addedAt || 0).getTime()
        );
        setSavedWatchedMovies(merged);

        const topGenres = await computeTopGenres(merged);
        if (isCancelled) return;
        setTopWatchedGenres(topGenres);
      } catch (err) {
        if (isCancelled) return;
        console.error("Failed to fetch watched movies:", err);
        setSavedWatchedMovies([]);
        setTopWatchedGenres([]);
      }
    };

    fetchWatchedMovies();

    return () => {
      isCancelled = true;
    };
  }, [isLoggedIn]);

  useEffect(() => {
    setWatchedPage(1);
  }, [savedWatchedMovies.length]);
  useEffect(() => {
    setWatchedPage(1);
  }, [normalizedWatchedSearch]);
  useEffect(() => {
    setReviewPage(1);
  }, [mergedReviewItems.length]);
  const watchedCount = posterItems.length;
  const reviewCount = mergedReviewItems.length;

  const handleOpenEdit = () => {
    setEditDraft(profile);
    setEditVisible(true);
    setPasswordVisible(false);
  };

  const handleOpenPassword = () => {
    setPasswordVisible(true);
    setEditVisible(false);
    setCurrentPassword("");
    setNextPassword("");
    setConfirmPassword("");
    setPasswordError(null);
    setPasswordSuccessVisible(false);
  };

  /*
  const handleKakaoLink = async () => {
    try {
      const response = await getKakaoLoginUrl();
      window.location.href = response.auth_url;
    } catch (err) {
      console.error("Failed to get Kakao login URL:", err);
      alert("카카오 로그인에 실패했습니다.");
    }
  };
  */

  const computeTopGenres = async (
    items: WatchedMovieItem[]
  ) => {
    const genreCounts = new Map<string, number>();

    const missingIds = new Set<number>();
    items.forEach((item) => {
      const genres = Array.isArray(item.genres) ? item.genres : null;
      if (genres && genres.length > 0) {
        genres.forEach((genre) => {
          if (typeof genre !== "string") return;
          const trimmed = genre.trim();
          if (!trimmed) return;
          genreCounts.set(trimmed, (genreCounts.get(trimmed) ?? 0) + 1);
        });
        return;
      }
      missingIds.add(item.movieId);
    });

    if (missingIds.size > 0) {
      await Promise.all(
        Array.from(missingIds).map(async (movieId) => {
          try {
            const movie = await getMovie(movieId);
            if (!movie?.genres || movie.genres.length === 0) return;
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
    }

    if (genreCounts.size === 0) return [];

    const maxCount = Math.max(...Array.from(genreCounts.values()));
    return Array.from(genreCounts.entries())
      .filter(([, count]) => count === maxCount)
      .map(([genre]) => genre)
      .sort((a, b) => a.localeCompare(b, "ko-KR"))
      .slice(0, 3);
  };

  const handleSaveProfile = async () => {
    const nextProfile: ProfileState = {
      nickname: editDraft.nickname.trim() || defaultProfile.nickname,
      realname: editDraft.realname.trim() || defaultProfile.realname,
      age: editDraft.age || "나이 정보 없음",
      gender: editDraft.gender || defaultProfile.gender,
      id: editDraft.id.trim() || defaultProfile.id,
      email: editDraft.email.trim() || defaultProfile.email,
      bio: editDraft.bio.trim() || defaultProfile.bio,
    };

    try {
      await updateCurrentUser({
        name: nextProfile.realname,
        nickname: nextProfile.nickname,
        email: nextProfile.email,
        gender: nextProfile.gender,
        birth_date: birthDate ?? undefined,
      });
    } catch (err) {
      console.error("Failed to update user profile:", err);
    }

    setProfile(nextProfile);
    setEditVisible(false);
    window.dispatchEvent(new Event("mw_auth_change"));
  };

  const handleCancelEdit = () => {
    setEditDraft(profile);
    setEditVisible(false);
  };

  const handlePasswordSave = async () => {
    if (isPasswordSaving) return;
    if (!currentUserId) {
      setPasswordError("세션 정보가 오래되었습니다. 다시 로그인해주세요.");
      return;
    }
    if (!currentPassword.trim() || !nextPassword.trim() || !confirmPassword.trim()) {
      setPasswordError("모든 비밀번호를 입력해주세요.");
      return;
    }
    if (nextPassword !== confirmPassword) {
      setPasswordError("새 비밀번호가 일치하지 않습니다.");
      return;
    }

    setIsPasswordSaving(true);
    setPasswordError(null);
    try {
      await changePassword({
        user_id: currentUserId,
        current_password: currentPassword,
        new_password: nextPassword,
        new_password_confirm: confirmPassword,
      });
      setPasswordVisible(false);
      setPasswordSuccessVisible(true);
      setCurrentPassword("");
      setNextPassword("");
      setConfirmPassword("");
    } catch (err) {
      console.error("Failed to change password:", err);
      setPasswordError("비밀번호 변경에 실패했습니다.");
    } finally {
      setIsPasswordSaving(false);
    }
  };

  const handlePasswordCancel = () => {
    setPasswordVisible(false);
    setCurrentPassword("");
    setNextPassword("");
    setConfirmPassword("");
    setPasswordError(null);
  };

  const handleLogout = () => {
    setAccessToken(null);
    window.dispatchEvent(new Event("mw_auth_change"));
    navigate("/login");
  };

  const handleDeleteRequest = () => {
    setDeleteConfirmVisible(true);
  };

  const handleDeleteCancel = () => {
    setDeleteConfirmVisible(false);
  };

  const handleDelete = async () => {
    if (isDeletingAccount) return;
    setIsDeletingAccount(true);
    try {
      await deleteCurrentUser();
      setAccessToken(null);
      window.dispatchEvent(new Event("mw_auth_change"));
      setDeleteConfirmVisible(false);
      setDeleteSuccessVisible(true);
    } catch (err) {
      console.error("Failed to delete user:", err);
      alert("회원 탈퇴에 실패했습니다.");
    } finally {
      setIsDeletingAccount(false);
    }
  };

  const handleRemoveWatchedMovie = async (movieId: number) => {
    try {
      await deleteCurrentUserWatchedMovie(movieId);
      setSavedWatchedMovies((prev) => {
        const next = prev.filter((item) => item.movieId !== movieId);
        void (async () => {
          const genreCounts = new Map<string, number>();
          await Promise.all(
            next.map(async (item) => {
              try {
                const movie = await getMovie(item.movieId);
                if (!movie?.genres) return;
                movie.genres.forEach((genre) => {
                  if (typeof genre !== "string") return;
                  const trimmed = genre.trim();
                  if (!trimmed) return;
                  genreCounts.set(trimmed, (genreCounts.get(trimmed) ?? 0) + 1);
                });
              } catch (err) {
                console.error(
                  `Failed to fetch movie genres for movie_id=${item.movieId}:`,
                  err
                );
              }
            })
          );

          if (genreCounts.size === 0) {
            setTopWatchedGenres([]);
            return;
          }

          const maxCount = Math.max(...Array.from(genreCounts.values()));
          const topGenres = Array.from(genreCounts.entries())
            .filter(([, count]) => count === maxCount)
            .map(([genre]) => genre)
            .sort((a, b) => a.localeCompare(b, "ko-KR"))
            .slice(0, 3);
          setTopWatchedGenres(topGenres);
        })();
        return next;
      });
    } catch (err) {
      console.error("Failed to delete watched movie:", err);
    }
  };

  const scrollToWithHeaderOffset = (elementId: string) => {
    const target = document.getElementById(elementId);
    if (!target) return;
    const header = document.querySelector<HTMLElement>(".top-bar");
    const headerOffset = header ? header.offsetHeight + 12 : 0;
    const targetTop = target.getBoundingClientRect().top + window.scrollY;
    window.scrollTo({
      top: Math.max(0, targetTop - headerOffset),
      behavior: "smooth",
    });
  };

  const requestScrollToSection = (targetId: string, nextView: ViewMode) => {
    if (view === nextView) {
      scrollToWithHeaderOffset(targetId);
      return;
    }
    pendingScrollTarget.current = targetId;
    setView(nextView);
  };

  const formatReviewRating = (rating: number) => {
    const ratingValue = Number.isFinite(rating)
      ? Math.max(0, Math.min(5, Math.round(rating * 2) / 2))
      : 0;
    return Number.isInteger(ratingValue)
      ? `${ratingValue}`
      : ratingValue.toFixed(1);
  };

  useEffect(() => {
    if (!pendingScrollTarget.current) return;
    const targetId = pendingScrollTarget.current;
    pendingScrollTarget.current = null;
    requestAnimationFrame(() => {
      scrollToWithHeaderOffset(targetId);
    });
  }, [view]);

  if (!isLoggedIn) {
    return (
      <MainLayout>
        <main className="container activity-page">
          <div className="activity-top-grid">
            <section className="section card taste-preview-section activity-top-card">
              <article className="taste-preview">
                <div className="taste-preview-header">
                  <h2>프로필</h2>
                </div>
                <p className="muted login-required-text">로그인 후 이용해주세요.</p>
              </article>
            </section>

            <section className="section card taste-preview-section activity-top-card">
              <article className="taste-preview">
                <div className="taste-preview-header">
                  <h2>취향 분석</h2>
                </div>
                <p className="muted login-required-text">로그인 후 이용해주세요.</p>
              </article>
            </section>

            <section className="section card activity-summary-card activity-top-card activity-top-card-full">
              <article className="taste-preview">
                <div className="taste-preview-header">
                  <h2>활동 요약</h2>
                  <p>내가 본 영화와 남긴 리뷰를 관리해요.</p>
                </div>
                <div className="activity-stats taste-preview-grid">
                  <div className="stat taste-preview-main">
                    <strong>–</strong>
                    <span>시청작</span>
                  </div>
                  <div className="stat taste-preview-side">
                    <strong>–</strong>
                    <span>리뷰</span>
                  </div>
                </div>
                <p className="muted login-required-text">로그인 후 이용 가능해요.</p>
              </article>
            </section>
          </div>
        </main>
      </MainLayout>
    );
  }

  return (
    <MainLayout>
      <main className="container activity-page">
        <div className="activity-top-grid">
          <section className="section card profile-card activity-top-card">
            {/* <div className="page-title">
            <h1>프로필</h1>
            <p>프로필과 설정을 관리해요.</p>
          </div> */}
            <div className="profile-header">
              <div className="profile-info">
                <div className="profile-top-row">
                  <div className="profile-summary">
                    <div className="profile-header-row">
                      <div className="profile-avatar-block">
                        <div className="profile-avatar is-image">
                          <img
                            className="profile-avatar-image"
                            src={ticketIcon}
                            alt={`${profile.nickname} 프로필`}
                          />
                        </div>
                        <h2 className="profile-nickname">{profile.nickname}</h2>
                      </div>
                      <button
                        className="icon-btn settings-btn"
                        type="button"
                        aria-label="설정 열기"
                        onClick={() => setSettingsOpen(true)}
                      >
                        ⚙
                      </button>
                    </div>
                  </div>
                  <div className="profile-divider" />
                  <div className="profile-meta">
                    <div>
                      <span className="muted">이름</span>
                      <strong>{profile.realname}</strong>
                    </div>
                    <div>
                      <span className="muted">나이</span>
                      <strong>{profile.age}</strong>
                    </div>
                    <div>
                      <span className="muted">성별</span>
                      <strong>{profile.gender}</strong>
                    </div>
                    <div>
                      <span className="muted">아이디</span>
                      <strong>{profile.id}</strong>
                    </div>
                    <div>
                      <span className="muted">이메일</span>
                      <strong>{profile.email}</strong>
                    </div>
                  </div>
                </div>
                {/* <div className="profile-actions">
                <button className="ghost-btn" type="button" onClick={handleLogout}>
                  로그아웃
                </button>
              </div> */}
              </div>
            </div>
            <p className="muted profile-bio profile-bio-below">"{profile.bio}"</p>
          </section>

          <section className="section card taste-preview-section activity-top-card">
            <article className="taste-preview">
              <div className="taste-preview-header with-cta">
                <div>
                  <h2>취향 분석 대시보드</h2>
                  <p>최근 평가 기반 요약</p>
                </div>
                <button
                  className="secondary-btn taste-preview-top-cta"
                  type="button"
                  onClick={() => navigate("/taste-analysis")}
                >
                  상세보기
                </button>
              </div>
              <div className="taste-preview-body taste-preview-grid">
                <div className="taste-preview-main">
                  <p className="muted">선호 키워드</p>
                  <div className="tag-list" style={{ marginTop: 8 }}>
                    <span className="tag">감정선</span>
                    <span className="tag">몰입</span>
                    <span className="tag">서사</span>
                  </div>
                </div>
                <div className="taste-preview-side">
                  <p className="muted">가장 높은 장르</p>
                  <p className="probability">{topGenreLabel}</p>
                </div>
              </div>
              {/* <button
              className="primary-btn taste-preview-cta"
              type="button"
              onClick={() => navigate("/taste-analysis")}
            >
              자세히보기
            </button> */}
            </article>
          </section>
        </div>

        <section className="section card activity-summary-card">
          <article className="taste-preview">

            {/*  
          <section className="page-title">
            <h1>내 활동</h1>
            <p>내가 본 영화와 남긴 리뷰를 관리해요.</p>
          </section> */}


            <div className="taste-preview-header">
              <h2>활동 요약</h2>
              <p>내가 본 영화와 남긴 리뷰를 관리해요.</p>
              {/* <p>시청/리뷰/컬렉션 현황</p> */}
            </div>
            <div className="activity-stats taste-preview-grid" id="activity-stats">
              <div
                className="stat taste-preview-main clickable hoverable"
                role="button"
                tabIndex={0}
                onClick={() => {
                  requestScrollToSection("activity-stats", "posters");
                }}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    requestScrollToSection("activity-stats", "posters");
                  }
                }}
              >
                <strong>{watchedCount}</strong>
                <span>시청작</span>
              </div>
              <div
                className="stat taste-preview-side clickable hoverable"
                role="button"
                tabIndex={0}
                onClick={() => {
                  requestScrollToSection("activity-stats", "reviews");
                }}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    requestScrollToSection("activity-stats", "reviews");
                  }
                }}
              >
                <strong>{reviewCount}</strong>
                <span>리뷰</span>
              </div>
            </div>
            {view === "posters" && (
              <article className="section view-section" data-view="posters" id="posters-section">
                <div
                  className="poster-search input-with-clear"
                  style={{ marginLeft: "auto", display: "flex", gap: 10, alignItems: "center" }}
                >
                  <input
                    className="search-input"
                    type="text"
                    placeholder="시청함에서 영화 검색"
                    value={watchedSearch}
                    onChange={(event) => setWatchedSearch(event.target.value)}
                    aria-label="시청함 영화 검색"
                    onKeyDown={(event) => {
                      if (event.key === "Enter") {
                        event.preventDefault();
                        setAppliedWatchedSearch(watchedSearch);
                      }
                    }}
                  />
                  {watchedSearch && (
                    <button
                      className="input-clear-btn"
                      type="button"
                      aria-label="검색어 지우기"
                      onClick={() => {
                        setWatchedSearch("");
                        setAppliedWatchedSearch("");
                      }}
                    >
                      ✕
                    </button>
                  )}
                  <button
                    className="primary-btn"
                    type="button"
                    onClick={() => setAppliedWatchedSearch(watchedSearch)}
                  >
                    검색
                  </button>
                </div>
                {filteredPosterItems.length === 0 ? (
                  <p className="search-empty">검색 결과가 없어요.</p>
                ) : (
                  <div className="poster-grid poster-grid-10">
                    {visiblePosters.map((poster) => (
                      <div key={poster.id} className="poster-card">
                        <Link to={poster.to}>
                          <img src={poster.src} alt={poster.alt} />
                        </Link>
                        <p className="poster-title">{poster.title}</p>
                        <button
                          className="poster-remove-btn"
                          type="button"
                          aria-label={`${poster.alt} 제거`}
                          onClick={(event) => {
                            event.preventDefault();
                            event.stopPropagation();
                            handleRemoveWatchedMovie(poster.movieId);
                          }}
                        >
                          ×
                        </button>
                      </div>
                    ))}
                  </div>
                )}
                {filteredPosterItems.length > WATCHED_PAGE_SIZE && (
                  <div className="poster-pagination">
                    <button
                      className="icon-btn page-arrow-btn"
                      type="button"
                      aria-label="이전 페이지"
                      onClick={() =>
                        setWatchedPage((prev) => Math.max(1, prev - 1))
                      }
                      disabled={safeWatchedPage === 1}
                    >
                      {"◀"}
                    </button>
                    <span className="page-number-text" aria-live="polite">
                      {safeWatchedPage}/{watchedTotalPages}
                    </span>
                    <button
                      className="icon-btn page-arrow-btn"
                      type="button"
                      aria-label="다음 페이지"
                      onClick={() =>
                        setWatchedPage((prev) =>
                          Math.min(watchedTotalPages, prev + 1)
                        )
                      }
                      disabled={safeWatchedPage >= watchedTotalPages}
                    >
                      {"▶"}
                    </button>
                  </div>
                )}
              </article>
            )}

            {view === "reviews" && (
              <article className="section view-section" data-view="reviews" id="reviews-section">
                <div className="review-list activity-review-grid">
                  {visibleReviews.map((review) => {
                    const visibilityMeta = getReviewVisibilityMeta(review.visibility);
                    const reviewText = review.content ?? "";
                    return (
                      <div className="review-item" key={review.id}>
                        <article
                          className="card review-card review-card-toggle"
                          role="button"
                          tabIndex={0}
                          onClick={() => navigate(`/movies/${review.movieId}#my-review`)}
                          onKeyDown={(event) => {
                            if (event.key === "Enter" || event.key === " ") {
                              event.preventDefault();
                              navigate(`/movies/${review.movieId}#my-review`);
                            }
                          }}
                        >
                          <Link
                            className="review-detail-link"
                            to={`/movies/${review.movieId}#my-review`}
                            onClick={(event) => event.stopPropagation()}
                          >
                            자세히보기
                          </Link>
                          <div className="movie-tile">
                            <div className="review-poster-block">
                              <img
                                className="poster"
                                src={review.poster}
                                alt={`${review.title} 포스터`}
                              />
                            </div>
                            <div className="movie-info">
                              <h3 className="review-title-row">
                                <span>{review.title}</span>
                                <span
                                  className={`review-visibility-indicator ${visibilityMeta.className}`}
                                  role="img"
                                  aria-label={visibilityMeta.label}
                                  title={visibilityMeta.label}
                                />
                              </h3>
                              <p className="muted">{review.dateLabel}</p>
                              <p className="muted">평점 {formatReviewRating(review.rating)}점</p>
                            </div>
                          </div>
                          <p className="muted review-summary-text review-summary-full">
                            {reviewText}
                          </p>
                        </article>
                      </div>
                    );
                  })}
                </div>
                {mergedReviewItems.length > REVIEWS_PAGE_SIZE && (
                  <div className="pagination">
                    <button
                      className="icon-btn page-arrow-btn"
                      type="button"
                      aria-label="이전 페이지"
                      onClick={() =>
                        setReviewPage((prev) => Math.max(1, prev - 1))
                      }
                      disabled={safeReviewPage === 1}
                    >
                      {"◀"}
                    </button>
                    <span className="page-number-text" aria-live="polite">
                      {safeReviewPage}/{reviewTotalPages}
                    </span>
                    <button
                      className="icon-btn page-arrow-btn"
                      type="button"
                      aria-label="다음 페이지"
                      onClick={() =>
                        setReviewPage((prev) =>
                          Math.min(reviewTotalPages, prev + 1)
                        )
                      }
                      disabled={safeReviewPage >= reviewTotalPages}
                    >
                      {"▶"}
                    </button>
                  </div>
                )}
              </article>
            )}
          </article>
        </section>
      </main>

      {settingsOpen && (
        <div
          className="modal"
          role="dialog"
          aria-modal="true"
          aria-labelledby="settings-title"
        >
          <div className="modal-overlay" onClick={() => setSettingsOpen(false)} />
          <div className="modal-content settings-modal">
            <div className="modal-scroll">
              <div className="modal-header">
                <h2 id="settings-title">설정</h2>
                <button
                  className="icon-btn"
                  type="button"
                  aria-label="설정 닫기"
                  onClick={() => setSettingsOpen(false)}
                >
                  ✕
                </button>
              </div>

              {/* <div className="modal-section">
                <h3>공개 설정</h3>
                <div className="toggle-row">
                  <span>프로필 공개</span>
                  <label className="toggle">
                    <input type="checkbox" defaultChecked />
                    <span />
                  </label>
                </div>
                <div className="toggle-row">
                  <span>리뷰 공개</span>
                  <label className="toggle">
                    <input type="checkbox" defaultChecked />
                    <span />
                  </label>
                </div>
              </div> */}

              <div className="modal-section">
                <h3>계정 설정</h3>
                <ul className="auth-actions support-actions">
                  <li>
                    <button
                      className="secondary-btn"
                      type="button"
                      onClick={handleOpenEdit}
                    >
                      프로필 수정
                    </button>
                  </li>
                  <li>
                    <button
                      className="secondary-btn"
                      type="button"
                      onClick={handleOpenPassword}
                    >
                      비밀번호 변경
                    </button>
                  </li>
                </ul>
              </div>

              {/*
              <div className="modal-section">
                <h3>SNS 연동 설정</h3>
                <ul className="auth-actions support-actions sns-link-list">
                  <li className="sns-link-item">
                    <span className="sns-label">카카오</span>
                    {isKakaoLinked ? (
                      <span className="sns-status connected">연결됨</span>
                    ) : (
                      <button
                        className="sns-status-link"
                        type="button"
                        onClick={handleKakaoLink}
                      >
                        연결안됨
                      </button>
                    )}
                  </li>
                  <li className="sns-link-item">
                    <span className="sns-label">구글</span>
                    {isGoogleLinked ? (
                      <span className="sns-status connected">연결됨</span>
                    ) : (
                      <span className="sns-status">연결안됨</span>
                    )}
                  </li>
                </ul>
              </div>
              */}

              <div className="modal-section">
                <h3>고객센터</h3>
                <ul className="auth-actions support-actions">
                  <li>
                    <Link className="secondary-btn" to="/notice">
                      공지사항
                    </Link>
                  </li>
                  <li>
                    <Link className="secondary-btn" to="/inquiry">
                      문의하기
                    </Link>
                  </li>
                  <li>
                    <Link className="secondary-btn" to="/faq">
                      FAQ
                    </Link>
                  </li>
                </ul>
              </div>

              <div className="modal-footer">
                <button className="secondary-btn" type="button" onClick={handleLogout}>
                  로그아웃
                </button>
                <button className="ghost-btn danger" type="button" onClick={handleDeleteRequest}>
                  탈퇴하기
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
      {editVisible && (
        <div
          className="modal"
          role="dialog"
          aria-modal="true"
          aria-labelledby="profile-edit-title"
        >
          <div className="modal-overlay" onClick={handleCancelEdit} />
          <div className="modal-content">
            <div className="modal-scroll">
              <div className="modal-header">
                <h2 id="profile-edit-title">프로필 수정</h2>
                <button
                  className="icon-btn"
                  type="button"
                  aria-label="프로필 수정 닫기"
                  onClick={handleCancelEdit}
                >
                  ✕
                </button>
              </div>
              <div className="profile-edit">
                <label htmlFor="profile-nickname-input">닉네임</label>
                <input
                  id="profile-nickname-input"
                  type="text"
                  value={editDraft.nickname}
                  onChange={(event) =>
                    setEditDraft((prev) => ({
                      ...prev,
                      nickname: event.target.value,
                    }))
                  }
                />
                <label htmlFor="profile-name-input">이름</label>
                <input
                  id="profile-name-input"
                  type="text"
                  value={editDraft.realname}
                  readOnly
                  aria-readonly="true"
                  onChange={(event) =>
                    setEditDraft((prev) => ({
                      ...prev,
                      realname: event.target.value,
                    }))
                  }
                />
                <label htmlFor="profile-age-input">나이</label>
                <input
                  id="profile-age-input"
                  type="text"
                  value={editDraft.age}
                  readOnly
                  aria-readonly="true"
                />
                <label htmlFor="profile-gender-input">성별</label>
                <div className="option-select" ref={genderSelectRef}>
                  <button
                    id="profile-gender-input"
                    type="button"
                    className={`option-select-trigger ${
                      !editDraft.gender || editDraft.gender === "선택 안함" ? "is-placeholder" : ""
                    }`}
                    onClick={() => setIsGenderSelectOpen((prev) => !prev)}
                  >
                    <span>{editDraft.gender || "선택 안함"}</span>
                    <span className="option-select-arrow">▾</span>
                  </button>
                  {isGenderSelectOpen && (
                    <div className="option-select-list">
                      {["선택 안함", "여성", "남성"].map((option) => (
                        <button
                          key={option}
                          type="button"
                          className="option-select-item"
                          onClick={() => {
                            setEditDraft((prev) => ({
                              ...prev,
                              gender: option,
                            }));
                            setIsGenderSelectOpen(false);
                          }}
                        >
                          <strong>{option}</strong>
                          {(editDraft.gender || "선택 안함") === option && <span>✓</span>}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
                <label htmlFor="profile-id-input">아이디</label>
                <input
                  id="profile-id-input"
                  type="text"
                  value={editDraft.id}
                  readOnly
                  aria-readonly="true"
                  onChange={(event) =>
                    setEditDraft((prev) => ({
                      ...prev,
                      id: event.target.value,
                    }))
                  }
                />
                <label htmlFor="profile-email-input">이메일</label>
                <input
                  id="profile-email-input"
                  type="email"
                  value={editDraft.email}
                  onChange={(event) =>
                    setEditDraft((prev) => ({
                      ...prev,
                      email: event.target.value,
                    }))
                  }
                />
                {/* <label htmlFor="profile-bio-input">한줄소개</label>
                <textarea
                  id="profile-bio-input"
                  value={editDraft.bio}
                  onChange={(event) =>
                    setEditDraft((prev) => ({
                      ...prev,
                      bio: event.target.value,
                    }))
                  }
                /> */}
                <div className="profile-edit-actions">
                  <button
                    className="primary-btn"
                    type="button"
                    onClick={handleSaveProfile}
                  >
                    저장
                  </button>
                  <button
                    className="ghost-btn"
                    type="button"
                    onClick={handleCancelEdit}
                  >
                    취소
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
      {passwordVisible && (
        <div
          className="modal"
          role="dialog"
          aria-modal="true"
          aria-labelledby="password-edit-title"
        >
          <div className="modal-overlay" onClick={handlePasswordCancel} />
          <div className="modal-content">
            <div className="modal-scroll">
              <div className="modal-header">
                <h2 id="password-edit-title">비밀번호 변경</h2>
                <button
                  className="icon-btn"
                  type="button"
                  aria-label="비밀번호 변경 닫기"
                  onClick={handlePasswordCancel}
                >
                  ✕
                </button>
              </div>
              <div className="profile-edit">
                <label htmlFor="password-current">현재 비밀번호</label>
                <input
                  id="password-current"
                  type="password"
                  placeholder="8~20자, 영문 대/소문자·숫자·특수문자 중 2가지 이상"
                  value={currentPassword}
                  onChange={(event) => setCurrentPassword(event.target.value)}
                />
                <label htmlFor="password-next">새 비밀번호</label>
                <input
                  id="password-next"
                  type="password"
                  placeholder="8~20자, 영문 대/소문자·숫자·특수문자 중 2가지 이상"
                  value={nextPassword}
                  onChange={(event) => setNextPassword(event.target.value)}
                />
                <label htmlFor="password-confirm">새 비밀번호 확인</label>
                <input
                  id="password-confirm"
                  type="password"
                  placeholder="8~20자, 영문 대/소문자·숫자·특수문자 중 2가지 이상"
                  value={confirmPassword}
                  onChange={(event) => setConfirmPassword(event.target.value)}
                />
                {passwordError && <p className="error">{passwordError}</p>}
                <div className="profile-edit-actions">
                  <button
                    className="primary-btn"
                    type="button"
                    onClick={handlePasswordSave}
                    disabled={isPasswordSaving}
                  >
                    {isPasswordSaving ? "변경 중..." : "변경"}
                  </button>
                  <button
                    className="ghost-btn"
                    type="button"
                    onClick={handlePasswordCancel}
                  >
                    취소
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
      {passwordSuccessVisible && (
        <div
          className="modal"
          role="dialog"
          aria-modal="true"
          aria-labelledby="password-success-title"
        >
          <div
            className="modal-overlay"
            onClick={() => setPasswordSuccessVisible(false)}
          />
          <div className="modal-content">
            <div className="modal-header">
              <h2 id="password-success-title">비밀번호 변경 완료</h2>
              <button
                className="icon-btn"
                type="button"
                aria-label="비밀번호 변경 완료 닫기"
                onClick={() => setPasswordSuccessVisible(false)}
              >
                ✕
              </button>
            </div>
            <div className="modal-scroll">
              <p>비밀번호가 변경되었습니다.</p>
              <div className="modal-footer">
                <button
                  className="primary-btn"
                  type="button"
                  onClick={() => setPasswordSuccessVisible(false)}
                >
                  확인
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
      {deleteConfirmVisible && (
        <div
          className="modal"
          role="dialog"
          aria-modal="true"
          aria-labelledby="delete-confirm-title"
        >
          <div className="modal-overlay" onClick={handleDeleteCancel} />
          <div className="modal-content">
            <div className="modal-header">
              <h2 id="delete-confirm-title">회원 탈퇴</h2>
              <button
                className="icon-btn"
                type="button"
                aria-label="회원 탈퇴 취소"
                onClick={handleDeleteCancel}
              >
                ✕
              </button>
            </div>
            <div className="modal-scroll">
              <p>정말 탈퇴하시겠어요?</p>
              <div className="modal-footer">
                <button className="ghost-btn" type="button" onClick={handleDeleteCancel}>
                  취소
                </button>
                <button
                  className="primary-btn"
                  type="button"
                  onClick={handleDelete}
                  disabled={isDeletingAccount}
                >
                  {isDeletingAccount ? "처리 중..." : "탈퇴하기"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
      {deleteSuccessVisible && (
        <div
          className="modal"
          role="dialog"
          aria-modal="true"
          aria-labelledby="delete-success-title"
        >
          <div
            className="modal-overlay"
            onClick={() => {
              setDeleteSuccessVisible(false);
              navigate("/login");
            }}
          />
          <div className="modal-content">
            <div className="modal-header">
              <h2 id="delete-success-title">탈퇴 완료</h2>
              <button
                className="icon-btn"
                type="button"
                aria-label="탈퇴 완료 닫기"
                onClick={() => {
                  setDeleteSuccessVisible(false);
                  navigate("/login");
                }}
              >
                ✕
              </button>
            </div>
            <div className="modal-scroll">
              <p>회원 탈퇴가 완료되었습니다.</p>
              <div className="modal-footer">
                <button
                  className="primary-btn"
                  type="button"
                  onClick={() => {
                    setDeleteSuccessVisible(false);
                    navigate("/login");
                  }}
                >
                  확인
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </MainLayout>
  );
}


const getReviewVisibilityMeta = (visibility: ReviewVisibility) =>
  visibility === "private"
    ? { className: "is-private", label: "비공개 리뷰" }
    : { className: "is-public", label: "공개 리뷰" };








