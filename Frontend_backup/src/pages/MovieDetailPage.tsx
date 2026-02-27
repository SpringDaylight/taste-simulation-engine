import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type KeyboardEvent as ReactKeyboardEvent,
  type MouseEvent as ReactMouseEvent,
} from "react";
import MainLayout from "../components/layout/MainLayout";
import SectionHeader from "../components/common/SectionHeader";
import { useLocation, useParams } from "react-router-dom";
import { getMovie, getMovieReviews, type Movie, type Review } from "../api/A2_movies";
import {
  createReview,
  createReviewComment,
  deleteReviewComment,
  updateReviewComment,
  deleteReview,
  getReviewComments,
  updateReview,
  toggleReviewLike,
  toggleCommentLike,
  type Comment as ReviewComment,
} from "../api/A6_reviews";
import { getCurrentUser, getCurrentUserReviews, getUser } from "../api/A7_profile";
import {
  getCurrentUserWatchedMovies,
  saveCurrentUserWatchedMovie,
  deleteCurrentUserWatchedMovie,
} from "../api/A8_watched";
import {
  explainPrediction,
  type SatisfactionPrediction,
  type PredictionExplanation
} from "../api/ml";
import { calculateMovieMatchRate } from "../utils/matchRateCalculator";
import { syncAfterReview } from "../utils/preferenceSync";
import { getAccessToken } from "../api/http";
import ReviewKeywordSelector, { KEYWORD_GROUPS, getKeywordLabel } from "../components/ReviewKeywordSelector";

const REVIEW_CONTENT_MAX_LENGTH = 500;

const formatRatingLabel = (rating: number) =>
  Number.isInteger(rating) ? `${rating}` : rating.toFixed(1);

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

const normalizeReviewRating = (value: number) => {
  if (!Number.isFinite(value)) return 5;
  return Math.max(0.5, Math.min(5, Math.round(value * 2) / 2));
};

type ReviewVisibility = "public" | "private";
type ReviewReaction = "like" | "dislike";

const toReviewVisibility = (isPublic?: boolean): ReviewVisibility =>
  isPublic === false ? "private" : "public";

const getReviewVisibilityMeta = (visibility: ReviewVisibility) =>
  visibility === "private"
    ? { className: "is-private", label: "비공개 리뷰" }
    : { className: "is-public", label: "공개 리뷰" };

const getStarFillPercent = (rating: number, starNumber: number) => {
  const normalized = normalizeReviewRating(rating);
  const fill = Math.max(0, Math.min(1, normalized - (starNumber - 1)));
  return Math.round(fill * 100);
};


export default function MovieDetailPage() {
  const { movieId } = useParams<{ movieId: string }>();
  const location = useLocation();
  const [movie, setMovie] = useState<Movie | null>(null);
  const [reviews, setReviews] = useState<Review[]>([]);
  const [reactions, setReactions] = useState<
    Record<number, { likes: number; dislikes: number }>
  >({});
  const [myReviewReactions, setMyReviewReactions] = useState<
    Record<number, ReviewReaction | null>
  >({});
  const [commentReactions, setCommentReactions] = useState<
    Record<number, { likes: number; dislikes: number }>
  >({});
  const [myCommentReactions, setMyCommentReactions] = useState<
    Record<number, ReviewReaction | null>
  >({});
  const [myReviewOpen, setMyReviewOpen] = useState(false);
  const [isEditingMyReview, setIsEditingMyReview] = useState(false);
  const [myReviewContent, setMyReviewContent] = useState("");
  const [myReviewRating, setMyReviewRating] = useState(5);
  const [hoverReviewRating, setHoverReviewRating] = useState<number | null>(null);
  const [myReviewVisibility, setMyReviewVisibility] =
    useState<ReviewVisibility>("public");
  const [myReviewKeywords, setMyReviewKeywords] = useState<string[]>([]);
  const [showKeywordErrors, setShowKeywordErrors] = useState(false);
  const [personalReviewVisibility, setPersonalReviewVisibility] =
    useState<ReviewVisibility>("public");
  const [isVisibilityOpen, setIsVisibilityOpen] = useState(false);
  const [showReviewLoginMessage, setShowReviewLoginMessage] = useState(false);
  const [reviewLoginMessageTick, setReviewLoginMessageTick] = useState(0);
  const [isMovieWatched, setIsMovieWatched] = useState(false);
  const [reviewDeleteConfirmOpen, setReviewDeleteConfirmOpen] = useState(false);
  const [isPersonalReviewDeleted, setIsPersonalReviewDeleted] = useState(false);
  const [isSavingMyReview, setIsSavingMyReview] = useState(false);
  const [isDeletingMyReview, setIsDeletingMyReview] = useState(false);
  const [myReviewErrorMessage, setMyReviewErrorMessage] = useState<string | null>(
    null
  );
  const [localPersonalReview, setLocalPersonalReview] = useState<Review | null>(
    null
  );
  const [replyDrafts, setReplyDrafts] = useState<Record<number, string>>({});
  const [replyOpen, setReplyOpen] = useState<Record<number, boolean>>({});
  const [commentOpen, setCommentOpen] = useState<Record<number, boolean>>({});
  const [reviewComments, setReviewComments] = useState<
    Record<number, ReviewComment[]>
  >({});
  const [commentLoading, setCommentLoading] = useState<Record<number, boolean>>(
    {}
  );
  const [commentErrors, setCommentErrors] = useState<Record<number, string | null>>(
    {}
  );

  const [commentEditing, setCommentEditing] = useState<Record<number, boolean>>({});
  const [commentEditDrafts, setCommentEditDrafts] = useState<Record<number, string>>({});
  const [reviewAuthorNames, setReviewAuthorNames] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [prediction, setPrediction] = useState<SatisfactionPrediction | null>(null);
  const [explanation, setExplanation] = useState<PredictionExplanation | null>(null);
  const [mlLoading, setMlLoading] = useState(false);
  const visibilitySelectRef = useRef<HTMLDivElement | null>(null);
  const isLoggedIn = Boolean(getAccessToken());
  const [currentUserPk, setCurrentUserPk] = useState<string | null>(null);
  const [currentUserNickname, setCurrentUserNickname] = useState("나");
  const personalReview = isPersonalReviewDeleted
    ? null
    : localPersonalReview;
  const personalReviewDate = personalReview?.created_at
    ? formatDateTime(personalReview.created_at)
    : formatDateTime();
  const reviewsForDisplay = useMemo(() => {
    if (!personalReview || !movie || personalReview.movie_id !== movie.id) {
      return reviews;
    }
    if (reviews.some((review) => review.id === personalReview.id)) {
      return reviews;
    }
    const merged = [personalReview, ...reviews];
    merged.sort(
      (a, b) =>
        new Date(b.created_at ?? 0).getTime() -
        new Date(a.created_at ?? 0).getTime()
    );
    return merged;
  }, [
    reviews,
    personalReview?.id,
    personalReview?.movie_id,
    personalReview?.is_public,
    movie?.id,
  ]);

  const otherReviewsForDisplay = useMemo(() => {
    const filtered = personalReview
      ? reviewsForDisplay.filter((review) => review.id !== personalReview.id)
      : reviewsForDisplay;
    if (!currentUserPk) return filtered;
    return filtered.filter(
      (review) => String(review.user_id) !== String(currentUserPk)
    );
  }, [reviewsForDisplay, personalReview?.id, currentUserPk]);

  // const averageRating = useMemo(() => {
  //   if (movie?.avg_rating !== null && movie?.avg_rating !== undefined) {
  //     return movie.avg_rating;
  //   }
  //   if (!reviews.length) return null;
  //   const sum = reviews.reduce((acc, review) => acc + (review.rating ?? 0), 0);
  //   return sum / reviews.length;
  // }, [movie?.avg_rating, reviews]);

  // const averageRatingPercent = useMemo(() => {
  //   if (averageRating === null) return 0;
  //   return Math.min(100, Math.max(0, (averageRating / 5) * 100));
  // }, [averageRating]);

  const normalizeText = (value?: string | null) =>
    typeof value === "string" ? value.normalize("NFC") : "";
  const movieTitle = normalizeText(movie?.title).trim() || "제목 정보 없음";
  const movieSynopsis =
    normalizeText(movie?.synopsis).trim() || "줄거리 정보가 없습니다.";
  const movieGenres = (movie?.genres ?? [])
    .map((genre) => normalizeText(genre).trim())
    .filter(Boolean);
  const movieTags = (movie?.tags ?? [])
    .map((tag) => normalizeText(tag).trim())
    .filter(Boolean);
  const genreSummary =
    movieGenres.length > 0 ? movieGenres.slice(0, 2).join("/") : "장르 정보 없음";
  const tagSummary = movieTags.slice(0, 5);

  const previewReviewRating = hoverReviewRating ?? myReviewRating;

  const getDisplayAuthorName = (authorId: string) => {
    if (currentUserPk && authorId === currentUserPk) {
      return normalizeText(currentUserNickname).trim() || "나";
    }
    return normalizeText(reviewAuthorNames[authorId] || authorId).trim() || "사용자";
  };

  useEffect(() => {
    setIsPersonalReviewDeleted(false);
    setReviewDeleteConfirmOpen(false);
    setIsEditingMyReview(false);
    setIsSavingMyReview(false);
    setIsDeletingMyReview(false);
    setMyReviewErrorMessage(null);
    setHoverReviewRating(null);
    setIsVisibilityOpen(false);
    const nextVisibility: ReviewVisibility = "public";
    setMyReviewVisibility(nextVisibility);
    setPersonalReviewVisibility(nextVisibility);
  }, [movieId, currentUserPk]);

  useEffect(() => {
    if (!isLoggedIn) {
      setCurrentUserNickname("나");
      setCurrentUserPk(null);
      return;
    }

    let isCancelled = false;
    getCurrentUser()
      .then((user) => {
        if (isCancelled) return;
        const name = normalizeText(
          user.nickname?.trim() ||
          user.name?.trim() ||
          user.user_id?.trim() ||
          user.id
        ).trim();
        setCurrentUserPk(user.id);
        setCurrentUserNickname(name || "나");
      })
      .catch((error) => {
        console.error("Failed to load current user:", error);
        if (!isCancelled) {
          setCurrentUserPk(null);
          setCurrentUserNickname("나");
        }
      });

    return () => {
      isCancelled = true;
    };
  }, [isLoggedIn]);

  useEffect(() => {
    const handleOutsideClick = (event: MouseEvent) => {
      if (!(event.target instanceof Node)) return;
      if (
        visibilitySelectRef.current &&
        !visibilitySelectRef.current.contains(event.target)
      ) {
        setIsVisibilityOpen(false);
      }
    };

    document.addEventListener("mousedown", handleOutsideClick);
    return () => {
      document.removeEventListener("mousedown", handleOutsideClick);
    };
  }, []);

  useEffect(() => {
    if (!movieId) return;
    setMyReviewVisibility("public");
    setPersonalReviewVisibility("public");

    if (!isLoggedIn) {
      setLocalPersonalReview(null);
      return;
    }

    let isCancelled = false;

    const fetchPersonalReview = async () => {
      try {
        const myReviews = await getCurrentUserReviews({
          page: 1,
          page_size: 100,
        });
        if (isCancelled) return;

        const match = myReviews.reviews.find(
          (item) => String(item.movie_id) === String(movieId)
        );
        setLocalPersonalReview(match ?? null);
        if (match) {
          const myVisibility = toReviewVisibility(match.is_public);
          setMyReviewVisibility(myVisibility);
          setPersonalReviewVisibility(myVisibility);
        }
      } catch (err) {
        if (isCancelled) return;
        console.error("Failed to fetch my review:", err);
        setLocalPersonalReview(null);
      }
    };

    fetchPersonalReview();

    return () => {
      isCancelled = true;
    };
  }, [movieId, isLoggedIn, currentUserPk]);

  useEffect(() => {
    if (!movieId) return;
    if (!isLoggedIn || !currentUserPk) {
      setIsMovieWatched(false);
      return;
    }

    let isCancelled = false;

    const fetchWatchedState = async () => {
      try {
        const watched = await getCurrentUserWatchedMovies({
          page: 1,
          page_size: 100,
        });
        if (isCancelled) return;
        const movieIdNumber = Number(movieId);
        setIsMovieWatched(
          watched.items.some((item) => Number(item.movie_id) === movieIdNumber)
        );
      } catch (err) {
        if (isCancelled) return;
        console.error("Failed to fetch watched movies:", err);
        setIsMovieWatched(false);
      }
    };

    fetchWatchedState();
    return () => {
      isCancelled = true;
    };
  }, [movieId, isLoggedIn, currentUserPk]);

  useEffect(() => {
    const fetchMovieData = async () => {
      if (!movieId) return;

      setLoading(true);
      setError(null);
      try {
        const movieData = await getMovie(Number(movieId));
        setMovie(movieData);

        const reviewsData = await getMovieReviews(Number(movieId), {
          page_size: 10,
        });
        const fetchedReviews = reviewsData.reviews;

        if (personalReview && personalReview.movie_id === movieData.id) {
          const hasPersonal = fetchedReviews.some(
            (review) => review.id === personalReview.id
          );
          const mergedReviews = hasPersonal
            ? fetchedReviews
            : [personalReview, ...fetchedReviews];
          mergedReviews.sort(
            (a, b) =>
              new Date(b.created_at ?? 0).getTime() -
              new Date(a.created_at ?? 0).getTime()
          );
          setReviews(mergedReviews);
        } else {
          setReviews(fetchedReviews);
        }

        // ML API: 사용자 취향 기반 영화 적합도 계산
        fetchMovieRecommendation(movieData);
      } catch (err) {
        setError("영화 정보를 불러오는데 실패했습니다.");
        console.error("Failed to fetch movie data:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchMovieData();
  }, [
    movieId,
    personalReview?.id,
    personalReview?.movie_id,
    personalReview?.is_public,
    currentUserPk,
  ]);

  useEffect(() => {
    if (!personalReview || !movie) return;
    if (personalReview.movie_id !== movie.id) return;
    setReviews((prev) => {
      if (prev.some((review) => review.id === personalReview.id)) return prev;
      const merged = [personalReview, ...prev];
      merged.sort(
        (a, b) =>
          new Date(b.created_at ?? 0).getTime() -
          new Date(a.created_at ?? 0).getTime()
      );
      return merged;
    });
  }, [personalReview?.id, personalReview?.movie_id, personalReview?.is_public, movie?.id]);

  useEffect(() => {
    if (location.hash !== "#my-review") return;
    const target = document.getElementById("my-review");
    if (!target) return;
    const timeout = window.setTimeout(() => {
      target.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 0);
    return () => window.clearTimeout(timeout);
  }, [location.hash, movie?.id]);

  useEffect(() => {
    setReactions((prev) => {
      const next: Record<number, { likes: number; dislikes: number }> = {};
      reviews.forEach((review) => {
        const existing = prev[review.id];
        next[review.id] = {
          likes: existing?.likes ?? review.likes_count ?? 0,
          dislikes: existing?.dislikes ?? review.dislikes_count ?? 0,
        };
      });
      return next;
    });
  }, [reviews]);

  useEffect(() => {
    setMyReviewReactions((prev) => {
      const next: Record<number, ReviewReaction | null> = {};
      reviews.forEach((review) => {
        next[review.id] = prev[review.id] ?? null;
      });
      return next;
    });
  }, [reviews]);

  useEffect(() => {
    const authorIds = new Set<string>();
    reviews.forEach((review) => {
      if (review.user_id) authorIds.add(review.user_id);
    });
    if (personalReview?.user_id) authorIds.add(personalReview.user_id);
    Object.values(reviewComments).forEach((commentList) => {
      commentList.forEach((comment) => {
        if (comment.user_id) authorIds.add(comment.user_id);
      });
    });

    const unresolvedIds = Array.from(authorIds).filter((authorId) => {
      if (currentUserPk && authorId === currentUserPk) return false;
      return !reviewAuthorNames[authorId];
    });

    if (unresolvedIds.length === 0) return;

    let isCancelled = false;

    const fetchAuthorNames = async () => {
      const fetchedEntries = await Promise.all(
        unresolvedIds.map(async (authorId) => {
          try {
            const user = await getUser(authorId);
            const displayName =
              user.nickname?.trim() ||
              user.name?.trim() ||
              user.user_id?.trim() ||
              authorId;
            return [authorId, displayName] as const;
          } catch (err) {
            console.error(`Failed to fetch user profile: ${authorId}`, err);
            return [authorId, authorId] as const;
          }
        })
      );

      if (isCancelled) return;
      setReviewAuthorNames((prev) => ({
        ...prev,
        ...Object.fromEntries(fetchedEntries),
      }));
    };

    fetchAuthorNames();

    return () => {
      isCancelled = true;
    };
  }, [
    reviews,
    personalReview?.user_id,
    currentUserPk,
    reviewAuthorNames,
    reviewComments,
  ]);

  const handleToggleReaction = async (reviewId: number, type: ReviewReaction) => {
    if (!isLoggedIn) {
      setShowReviewLoginMessage(true);
      setReviewLoginMessageTick((prev) => prev + 1);
      return;
    }
    if (!currentUserPk) return;

    const currentReaction = myReviewReactions[reviewId] ?? null;
    if (currentReaction && currentReaction !== type) {
      return;
    }

    try {
      const response = await toggleReviewLike(reviewId, type === "like");
      const nextReaction = currentReaction === type ? null : type;
      setReactions((prev) => ({
        ...prev,
        [reviewId]: {
          likes: response.likes_count,
          dislikes: response.dislikes_count,
        },
      }));
      setMyReviewReactions((prev) => ({
        ...prev,
        [reviewId]: nextReaction,
      }));
    } catch (err) {
      console.error("Failed to toggle review reaction:", err);
    }
  };

  const handleToggleCommentReaction = async (
    reviewId: number,
    commentId: number,
    type: ReviewReaction
  ) => {
    if (!isLoggedIn) {
      setCommentErrors((prev) => ({
        ...prev,
        [reviewId]: "로그인 후 좋아요/싫어요를 눌러주세요.",
      }));
      return;
    }
    const currentReaction = myCommentReactions[commentId] ?? null;
    if (currentReaction && currentReaction !== type) {
      return;
    }

    try {
      const response = await toggleCommentLike(commentId, type === "like");
      const nextReaction = currentReaction === type ? null : type;
      setCommentReactions((prev) => ({
        ...prev,
        [commentId]: {
          likes: response.likes_count,
          dislikes: response.dislikes_count,
        },
      }));
      setMyCommentReactions((prev) => ({
        ...prev,
        [commentId]: nextReaction,
      }));
    } catch (err) {
      console.error("Failed to toggle comment reaction:", err);
    }
  };

  const applySavedPersonalReview = async (nextReview: Review) => {
    const nextVisibility = toReviewVisibility(nextReview.is_public);
    setLocalPersonalReview(nextReview);
    setMyReviewVisibility(nextVisibility);
    setPersonalReviewVisibility(nextVisibility);
    setIsPersonalReviewDeleted(false);
    setIsEditingMyReview(false);
    setShowReviewLoginMessage(false);
    setMyReviewOpen(false);
    setHoverReviewRating(null);
    setIsVisibilityOpen(false);
    setMyReviewErrorMessage(null);

    // 리뷰 저장 후 사용자 선호도 동기화
    if (currentUserPk) {
      try {
        await syncAfterReview(currentUserPk);
        // 선호도가 업데이트되었으므로 적합도 재계산
        if (movie) {
          setMlLoading(true);
          await fetchMovieRecommendation(movie);
        }
      } catch (err) {
        console.error("Failed to sync preference after review:", err);
      }
    }
  };

  const handleMyReviewSave = async () => {
    if (!movie || isSavingMyReview) return;
    if (!isLoggedIn) {
      setShowReviewLoginMessage(true);
      setReviewLoginMessageTick((prev) => prev + 1);
      return;
    }

    if (!currentUserPk) {
      setMyReviewErrorMessage(
        "세션 정보가 오래되었습니다. 로그아웃 후 다시 로그인해주세요."
      );
      return;
    }
    // 키워드 필수 검증 (각 그룹당 1개 이상)
    const hasAllGroupsSelected = KEYWORD_GROUPS.every((group: any) =>
      group.items.some((item: any) => myReviewKeywords.includes(item.value))
    );

    if (!hasAllGroupsSelected) {
      setShowKeywordErrors(true);
      setMyReviewErrorMessage("각 그룹마다 감상 키워드를 최소 1개 이상 선택해주세요.");
      return;
    }

    const content = myReviewContent.trim().slice(0, REVIEW_CONTENT_MAX_LENGTH);
    const reviewPayload = {
      rating: normalizeReviewRating(myReviewRating),
      content: content.length ? content : null,
      keywords: myReviewKeywords,
      is_public: myReviewVisibility === "public",
    };

    setIsSavingMyReview(true);
    setMyReviewErrorMessage(null);

    try {
      let nextReview: Review;
      if (personalReview?.id) {
        nextReview = await updateReview(personalReview.id, reviewPayload);
      } else {
        nextReview = await createReview({
          movie_id: movie.id,
          ...reviewPayload,
        });
      }
      await applySavedPersonalReview(nextReview);
      if (movie?.id) {
        try {
          await saveCurrentUserWatchedMovie({ movie_id: movie.id });
        } catch (watchErr) {
          console.warn("Failed to sync watched movie after review:", watchErr);
        }
        setIsMovieWatched(true);
      }

      // 리뷰 작성 후 취향 업데이트
      try {
        if (currentUserPk && movie?.id) {
          const { updatePreferenceFromReview } = await import("../api/userPreferences");
          await updatePreferenceFromReview(
            currentUserPk,
            movie.id,
            reviewPayload.rating,
            reviewPayload.content || undefined  // 리뷰 텍스트도 전달
          );
          console.log("User preference updated based on review");
        }
      } catch (prefError) {
        console.warn("Failed to update preference from review:", prefError);
        // 취향 업데이트 실패해도 리뷰는 저장됨
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "리뷰 저장에 실패했습니다.";

      if (
        !personalReview?.id &&
        typeof message === "string" &&
        message.toLowerCase().includes("already reviewed")
      ) {
        try {
          const myReviews = await getCurrentUserReviews({
            page: 1,
            page_size: 100,
          });
          const existingReview = myReviews.reviews.find(
            (item) => item.movie_id === movie.id
          );
          if (existingReview) {
            const updatedReview = await updateReview(existingReview.id, reviewPayload);
            await applySavedPersonalReview(updatedReview);
            return;
          }
        } catch (fallbackErr) {
          console.error("Failed to recover already-reviewed state:", fallbackErr);
        }
      }

      console.error("Failed to save review:", err);
      setMyReviewErrorMessage(message);
    } finally {
      setIsSavingMyReview(false);
    }
  };

  const handleMyReviewEditOpen = () => {
    if (!personalReview) return;
    setMyReviewRating(normalizeReviewRating(personalReview.rating ?? 5));
    setMyReviewContent(
      (personalReview.content ?? "").slice(0, REVIEW_CONTENT_MAX_LENGTH)
    );
    // TypeScript err: Property 'keywords' does not exist on type 'Review' (A6_reviews.ts has keywords?: string[])
    // Cast to any locally or use as string[]
    setMyReviewKeywords((personalReview as any).keywords ?? []);
    setShowKeywordErrors(false);
    setMyReviewVisibility(personalReviewVisibility);
    setIsEditingMyReview(true);
    setShowReviewLoginMessage(false);
    setMyReviewErrorMessage(null);
    setMyReviewOpen(true);
    setHoverReviewRating(null);
    setIsVisibilityOpen(false);
  };

  const handleMyReviewDeleteConfirm = async () => {
    if (!movie || !personalReview || isDeletingMyReview) return;
    setIsDeletingMyReview(true);
    setMyReviewErrorMessage(null);

    try {
      await deleteReview(personalReview.id);
    } catch (err) {
      const message = err instanceof Error ? err.message : "리뷰 삭제에 실패했습니다.";
      console.error("Failed to delete review:", err);
      setMyReviewErrorMessage(message);
      setIsDeletingMyReview(false);
      return;
    }

    setLocalPersonalReview(null);
    setIsPersonalReviewDeleted(true);
    setIsEditingMyReview(false);
    setMyReviewOpen(false);
    setHoverReviewRating(null);
    setShowReviewLoginMessage(false);
    setMyReviewVisibility("public");
    setPersonalReviewVisibility("public");
    setIsVisibilityOpen(false);
    setReviewDeleteConfirmOpen(false);
    setIsDeletingMyReview(false);
  };

  const handleMarkWatched = async () => {
    if (!movie) return;
    if (!isLoggedIn) {
      setShowReviewLoginMessage(true);
      setReviewLoginMessageTick((prev) => prev + 1);
      return;
    }
    if (!currentUserPk) return;

    try {
      if (isMovieWatched) {
        // 이미 시청함 → 제거
        await deleteCurrentUserWatchedMovie(movie.id);
        setIsMovieWatched(false);
      } else {
        // 시청 안 함 → 추가
        await saveCurrentUserWatchedMovie({ movie_id: movie.id });
        setIsMovieWatched(true);
      }
    } catch (err) {
      console.error("Failed to toggle watched movie:", err);
    }
  };

  const resolveRatingFromPointer = (
    event: ReactMouseEvent<HTMLSpanElement>,
    starNumber: number
  ) => {
    const rect = event.currentTarget.getBoundingClientRect();
    const pointerX = event.clientX - rect.left;
    const isLeftHalf = pointerX < rect.width / 2;
    const nextValue = starNumber - (isLeftHalf ? 0.5 : 0);
    return normalizeReviewRating(nextValue);
  };

  const handleReviewRatingHover = (
    event: ReactMouseEvent<HTMLSpanElement>,
    starNumber: number
  ) => {
    if (!isLoggedIn) return;
    setHoverReviewRating(resolveRatingFromPointer(event, starNumber));
  };

  const handleReviewRatingSelect = (
    event: ReactMouseEvent<HTMLSpanElement>,
    starNumber: number
  ) => {
    if (!isLoggedIn) return;
    const nextRating = resolveRatingFromPointer(event, starNumber);
    setMyReviewRating(nextRating);
    setHoverReviewRating(nextRating);
  };

  const handleReviewRatingKeyDown = (event: ReactKeyboardEvent<HTMLDivElement>) => {
    if (!isLoggedIn) return;

    let nextRating = myReviewRating;

    switch (event.key) {
      case "ArrowRight":
      case "ArrowUp":
        nextRating = normalizeReviewRating(myReviewRating + 0.5);
        break;
      case "ArrowLeft":
      case "ArrowDown":
        nextRating = normalizeReviewRating(myReviewRating - 0.5);
        break;
      case "Home":
        nextRating = 0.5;
        break;
      case "End":
        nextRating = 5;
        break;
      default:
        return;
    }

    event.preventDefault();
    setMyReviewRating(nextRating);
    setHoverReviewRating(null);
  };
  const toggleReplyOpen = (reviewId: number) => {
    setReplyOpen((prev) => ({
      ...prev,
      [reviewId]: !prev[reviewId],
    }));
  };

  const loadReviewComments = async (reviewId: number) => {
    setCommentLoading((prev) => ({ ...prev, [reviewId]: true }));
    setCommentErrors((prev) => ({ ...prev, [reviewId]: null }));
    try {
      const apiComments = await getReviewComments(reviewId);
      setReviewComments((prev) => ({ ...prev, [reviewId]: apiComments }));
      setCommentReactions((prev) => {
        const next = { ...prev };
        apiComments.forEach((comment) => {
          next[comment.id] = {
            likes: comment.likes_count ?? 0,
            dislikes: comment.dislikes_count ?? 0,
          };
        });
        return next;
      });
    } catch (err) {
      console.error("Failed to fetch review comments:", err);
      setCommentErrors((prev) => ({
        ...prev,
        [reviewId]: "댓글을 불러오지 못했습니다.",
      }));
    } finally {
      setCommentLoading((prev) => ({ ...prev, [reviewId]: false }));
    }
  };

  const toggleCommentOpen = (reviewId: number) => {
    setCommentOpen((prev) => {
      const nextOpen = !prev[reviewId];
      if (nextOpen) {
        void loadReviewComments(reviewId);
      }
      return { ...prev, [reviewId]: nextOpen };
    });
  };

  const handleReplyChange = (reviewId: number, value: string) => {
    setReplyDrafts((prev) => ({
      ...prev,
      [reviewId]: value,
    }));
  };

  const handleReplySubmit = async (reviewId: number) => {
    const nextValue = (replyDrafts[reviewId] || "").trim();
    if (!nextValue) return;
    if (!isLoggedIn) {
      setCommentErrors((prev) => ({
        ...prev,
        [reviewId]: "로그인 후 댓글을 작성해주세요.",
      }));
      return;
    }
    setReplyDrafts((prev) => ({ ...prev, [reviewId]: "" }));
    setReplyOpen((prev) => ({ ...prev, [reviewId]: false }));

    try {
      const createdComment = await createReviewComment(reviewId, {
        content: nextValue,
      });
      setReviewComments((prev) => ({
        ...prev,
        [reviewId]: [...(prev[reviewId] || []), createdComment],
      }));
      setCommentReactions((prev) => ({
        ...prev,
        [createdComment.id]: {
          likes: createdComment.likes_count ?? 0,
          dislikes: createdComment.dislikes_count ?? 0,
        },
      }));
      setCommentOpen((prev) => ({ ...prev, [reviewId]: true }));
    } catch (err) {
      console.error("Failed to save comment to API:", err);
      setCommentErrors((prev) => ({
        ...prev,
        [reviewId]: "댓글 저장에 실패했습니다.",
      }));
    }
  };



  const handleCommentDelete = async (reviewId: number, commentId: number) => {
    if (!isLoggedIn) return;

    try {
      await deleteReviewComment(commentId);
      setReviewComments((prev) => ({
        ...prev,
        [reviewId]: (prev[reviewId] || []).filter((comment) => comment.id != commentId),
      }));
      setCommentReactions((prev) => {
        const next = { ...prev };
        delete next[commentId];
        return next;
      });
      setMyCommentReactions((prev) => {
        const next = { ...prev };
        delete next[commentId];
        return next;
      });
    } catch (err) {
      console.error("Failed to delete comment:", err);
      setCommentErrors((prev) => ({
        ...prev,
        [reviewId]: "댓글 삭제에 실패했습니다.",
      }));
    }
  };



  const handleCommentEditOpen = (commentId: number, content: string) => {
    setCommentEditDrafts((prev) => ({
      ...prev,
      [commentId]: content,
    }));
    setCommentEditing((prev) => ({
      ...prev,
      [commentId]: true,
    }));
  };

  const handleCommentEditChange = (commentId: number, value: string) => {
    setCommentEditDrafts((prev) => ({
      ...prev,
      [commentId]: value,
    }));
  };

  const handleCommentEditCancel = (commentId: number) => {
    setCommentEditing((prev) => ({
      ...prev,
      [commentId]: false,
    }));
  };

  const handleCommentEditSave = async (reviewId: number, commentId: number) => {
    if (!isLoggedIn) return;
    const nextValue = (commentEditDrafts[commentId] || "").trim();
    if (!nextValue) {
      setCommentErrors((prev) => ({
        ...prev,
        [reviewId]: "댓글 내용을 입력해주세요.",
      }));
      return;
    }

    try {
      const updated = await updateReviewComment(commentId, {
        content: nextValue,
      });
      setReviewComments((prev) => ({
        ...prev,
        [reviewId]: (prev[reviewId] || []).map((comment) =>
          comment.id === commentId ? { ...comment, content: updated.content } : comment
        ),
      }));
      setCommentEditing((prev) => ({
        ...prev,
        [commentId]: false,
      }));
    } catch (err) {
      console.error("Failed to update comment:", err);
      setCommentErrors((prev) => ({
        ...prev,
        [reviewId]: "댓글 수정에 실패했습니다.",
      }));
    }
  };

  const personalReviewVisibilityMeta = getReviewVisibilityMeta(
    personalReviewVisibility
  );

  const fetchMovieRecommendation = async (movieData: Movie) => {
    setMlLoading(true);
    try {
      // 공통 유틸리티 함수 사용
      const result = await calculateMovieMatchRate(movieData);

      if (!result) {
        // 취향 정보가 없으면 ML API 호출 안 함
        return;
      }

      setPrediction(result);

      // 설명 생성
      const explanationResult = await explainPrediction({
        movie_title: movieData.title,
        match_rate: result.match_rate,
        probability: result.probability,
        breakdown: result.breakdown,
        user_liked_tags: [], // calculateMovieMatchRate에서 이미 계산됨
        user_disliked_tags: [],
      });
      setExplanation(explanationResult);
    } catch (err) {
      console.error('Failed to fetch ML recommendation:', err);
      // ML API 실패는 치명적이지 않으므로 에러 표시 안 함
    } finally {
      setMlLoading(false);
    }
  };

  if (loading) {
    return (
      <MainLayout>
        <main className="container movie-detail-page">
          <p>로딩 중...</p>
        </main>
      </MainLayout>
    );
  }

  if (error || !movie) {
    return (
      <MainLayout>
        <main className="container movie-detail-page">
          <p className="error">{error || "영화를 찾을 수 없습니다."}</p>
        </main>
      </MainLayout>
    );
  }

  return (
    <MainLayout>
      <main className="container movie-detail-page">
        {/* <section className="page-title">
          <h1>영화 자세히보기</h1>
          <p>영화를 선택하면 상세 정보와 취향 적합도를 확인할 수 있어요.</p>
        </section> */}

        <section className="section">
          <article className="movie-detail-main-card">
            {/* {averageRating !== null && (
              <div className="movie-detail-rating">
                <span className="movie-detail-rating-label">평균 평점</span>
                <span className="movie-detail-rating-stars" aria-label={`평점 ${averageRating.toFixed(1)}`}>
                  <span className="movie-detail-rating-stars-base">★★★★★</span>
                  <span
                    className="movie-detail-rating-stars-fill"
                    style={{ width: `${averageRatingPercent}%` }}
                    aria-hidden="true"
                  >
                    ★★★★★
                  </span>
                </span>
                <span className="movie-detail-rating-value">{averageRating.toFixed(1)}</span>
              </div>
            )} */}
            <div className="movie-tile">
              <img
                className="poster"
                src={
                  movie.poster_url ||
                  "https://via.placeholder.com/500x750?text=No+Image"
                }
                alt={`${movieTitle} 포스터`}
              />
              <div className="movie-info">
                <div className="movie-title-row">
                  <h2 style={{ marginTop: 6 }}>{movieTitle}</h2>
                  <button
                    className={`ghost-btn movie-detail-watch-btn ${isMovieWatched ? "is-active" : ""
                      }`}
                    type="button"
                    onClick={handleMarkWatched}
                  >
                    시청함
                  </button>
                </div>
                <p className="muted">
                  {movie.release
                    ? new Date(movie.release).getFullYear()
                    : "미정"}{" "}
                  · {genreSummary} ·{" "}
                  {movie.runtime ? `${movie.runtime}분` : "정보 없음"}
                </p>
                <div className="section synopsis-card" style={{ marginTop: 18 }}>
                  <h3>줄거리</h3>
                  <p className="muted synopsis-text">
                    {movieSynopsis}
                  </p>
                </div>
                <div className="tag-list" style={{ marginTop: 10 }}>
                  {tagSummary.map((tag) => (
                    <span key={tag} className="tag">{tag}</span>
                  ))}
                </div>
              </div>
            </div>

            <div className="section" style={{ marginTop: 18 }}>
              {/* <h3>나와의 적합도</h3> */}
              {mlLoading ? (
                <p className="muted">분석 중...</p>
              ) : prediction ? (
                <>
                  <p className="probability">
                    {`이 영화는 ${currentUserNickname}님과 ${Math.round(
                      prediction.match_rate
                    )}% 잘 맞아요`}
                  </p>
                  {explanation ? (
                    <>
                      <p className="muted" style={{ marginTop: 8, marginBottom: 12 }}>
                        {explanation.explanation}
                      </p>
                      <ul className="list">
                        {explanation.key_factors.slice(0, 3).map((factor, idx) => (
                          <li key={idx}>
                            {factor.label}: {Math.round(factor.score * 100)}% 일치
                          </li>
                        ))}
                      </ul>
                    </>
                  ) : (
                    <ul className="list">
                      <li>거대한 세계관과 몰입도 높은 전개를 선호하셨어요.</li>
                      <li>가족 서사가 중심인 작품을 좋아하셨어요.</li>
                      <li>유사 취향 사용자 반응이 긍정적이었어요.</li>
                    </ul>
                  )}
                </>
              ) : (
                <>
                  <p className="probability">
                    {`이 영화는 ${currentUserNickname}님과 83% 잘 맞아요`}
                  </p>
                  <ul className="list">
                    <li>거대한 세계관과 몰입도 높은 전개를 선호하셨어요.</li>
                    <li>가족 서사가 중심인 작품을 좋아하셨어요.</li>
                    <li>유사 취향 사용자 반응이 긍정적이었어요.</li>
                  </ul>
                </>
              )}
            </div>

            {prediction && prediction.breakdown.dislike_penalty > 0 && (
              <div className="section" style={{ marginTop: 18 }}>
                <h3>주의할 점</h3>
                <p className="muted">
                  선호하지 않는 요소가 일부 포함되어 있을 수 있습니다.
                </p>
              </div>
            )}

            {/* <div className="hero-actions" style={{ marginTop: 18 }}>
              <button className="ghost-btn movie-detail-watch-btn is-active">바로 감상하기</button>
            </div> */}
          </article>
        </section>

        <section className="section" id="my-review">
          <SectionHeader title="내 리뷰" />
          {personalReview && personalReview.movie_id === movie.id && !myReviewOpen ? (
            <div className="review-item">
              <article className="card review-card">
                <div className="review-header">
                  <div className="review-user">
                    <div className="review-avatar">
                      {getDisplayAuthorName(personalReview.user_id).substring(0, 2).toUpperCase()}
                    </div>
                    <div>
                      <p className="review-name" style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                        {getDisplayAuthorName(personalReview.user_id)}
                        <span
                          className={`review-visibility-indicator ${personalReviewVisibilityMeta.className}`}
                          role="img"
                          aria-label={personalReviewVisibilityMeta.label}
                          title={personalReviewVisibilityMeta.label}
                        />
                      </p>
                      <div className="review-rating-mini" style={{ display: 'flex', alignItems: 'center', gap: '0.1rem', marginTop: '0.2rem' }}>
                        {Array.from({ length: 5 }, (_, i) => {
                          const isFilled = i < Math.floor(personalReview.rating ?? 0);
                          const isHalf = !isFilled && i < (personalReview.rating ?? 0);
                          return isHalf ? (
                            <span key={i} style={{ position: 'relative', display: 'inline-block', fontSize: '1rem', lineHeight: 1 }}>
                              <span style={{ color: '#cbd5e1' }}>★</span>
                              <span style={{ position: 'absolute', top: 0, left: 0, width: '50%', overflow: 'hidden', color: '#fbbf24' }}>★</span>
                            </span>
                          ) : (
                            <span key={i} style={{ color: isFilled ? '#fbbf24' : '#cbd5e1', fontSize: '1rem', lineHeight: 1 }}>
                              ★
                            </span>
                          );
                        })}
                        <span style={{ fontSize: '0.85rem', color: '#64748b', marginLeft: '0.3rem' }}>
                          평점 {formatRatingLabel(personalReview.rating)}
                        </span>
                      </div>
                    </div>
                  </div>
                  <div className="review-actions">
                    <button
                      className="ghost-btn review-reaction-btn"
                      type="button"
                      aria-label="좋아요"
                      aria-pressed={false}
                      disabled
                    >
                      <span className="review-reaction-icon" aria-hidden="true" />
                      {reactions[personalReview.id]?.likes ??
                        personalReview.likes_count ??
                        0}
                    </button>
                    <button
                      className="ghost-btn review-reaction-btn"
                      type="button"
                      aria-label="싫어요"
                      aria-pressed={false}
                      disabled
                    >
                      <span
                        className="review-reaction-icon is-dislike"
                        aria-hidden="true"
                      />
                      {reactions[personalReview.id]?.dislikes ??
                        personalReview.dislikes_count ??
                        0}
                    </button>
                  </div>
                </div>
                {(() => {
                  const keywords = (personalReview as any).keywords as string[] | undefined;
                  return (
                    <>
                      {keywords && keywords.length > 0 && (
                        <div className="review-keywords-badges" style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem', marginBottom: '0.5rem' }}>
                          {keywords.map((k) => (
                            <span key={k} className="review-keyword-badge" style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              padding: '0.25rem 0.6rem',
                              backgroundColor: '#f8fafc',
                              color: '#475569',
                              borderRadius: '9999px',
                              fontSize: '0.8rem',
                              fontWeight: 500,
                              border: '1px solid #e2e8f0'
                            }}>
                              #{getKeywordLabel(k)}
                            </span>
                          ))}
                        </div>
                      )}
                      {(personalReview.content || !keywords?.length) && (
                        <p className="review-text">
                          {personalReview.content || "리뷰 코멘트가 없습니다."}
                        </p>
                      )}
                    </>
                  );
                })()}
                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem', marginBottom: '0.5rem' }}>
                  <button
                    className="ghost-btn review-link-btn"
                    type="button"
                    onClick={handleMyReviewEditOpen}
                  >
                    리뷰 수정
                  </button>
                  <button
                    className="ghost-btn review-link-btn"
                    type="button"
                    onClick={() => setReviewDeleteConfirmOpen(true)}
                  >
                    리뷰 삭제
                  </button>
                </div>
                <div className="review-link-row" style={{ display: 'flex', alignItems: 'center', marginTop: '0.5rem' }}>
                  <button
                    className="ghost-btn review-link-btn"
                    type="button"
                    onClick={() => toggleCommentOpen(personalReview.id)}
                  >
                    댓글({reviewComments[personalReview.id]?.length ?? personalReview.comments_count ?? 0})
                  </button>
                  <button
                    className="ghost-btn review-link-btn"
                    type="button"
                    onClick={() => toggleReplyOpen(personalReview.id)}
                  >
                    댓글 달기
                  </button>
                  <div style={{ marginLeft: 'auto', fontSize: '0.8rem', color: '#94a3b8' }}>
                    {personalReviewDate}
                  </div>
                </div>
                {replyOpen[personalReview.id] && (
                  <div className="review-reply-form">
                    <textarea
                      className="review-reply-input"
                      placeholder="댓글을 입력하세요"
                      value={replyDrafts[personalReview.id] || ""}
                      onChange={(event) =>
                        handleReplyChange(personalReview.id, event.target.value)
                      }
                    />
                    <div className="review-reply-actions">
                      <button
                        className="primary-btn review-reply-submit"
                        type="button"
                        onClick={() => handleReplySubmit(personalReview.id)}
                      >
                        저장하기
                      </button>
                    </div>
                  </div>
                )}
              </article>
              {commentOpen[personalReview.id] && (
                <div className="comment-thread">
                  <div className="comment-list">
                    {commentLoading[personalReview.id] ? (
                      <p className="muted">댓글을 불러오는 중...</p>
                    ) : (reviewComments[personalReview.id] || []).length > 0 ? (
                      (reviewComments[personalReview.id] || []).map((comment) => (
                        <div className="comment-card" key={comment.id}>
                          <div className="comment-meta">
                            <span className="review-name">
                              {getDisplayAuthorName(comment.user_id)}
                            </span>
                            <span className="muted">
                              {formatDateTime(comment.created_at)}
                            </span>
                            <div className="comment-reactions">
                              {(() => {
                                const reaction = myCommentReactions[comment.id] ?? null;
                                const likeActive = reaction === "like";
                                const dislikeActive = reaction === "dislike";
                                const isOwnComment =
                                  Boolean(currentUserPk) &&
                                  String(comment.user_id) === String(currentUserPk);
                                return (
                                  <>
                                    <button
                                      className={`ghost-btn review-reaction-btn ${likeActive ? "is-active" : ""
                                        }`}
                                      type="button"
                                      aria-label="좋아요"
                                      aria-pressed={likeActive}
                                      disabled={dislikeActive || isOwnComment}
                                      onClick={() =>
                                        handleToggleCommentReaction(
                                          personalReview.id,
                                          comment.id,
                                          "like"
                                        )
                                      }
                                    >
                                      <span
                                        className="review-reaction-icon"
                                        aria-hidden="true"
                                      />
                                      {commentReactions[comment.id]?.likes ??
                                        comment.likes_count ??
                                        0}
                                    </button>
                                    <button
                                      className={`ghost-btn review-reaction-btn ${dislikeActive ? "is-active" : ""
                                        }`}
                                      type="button"
                                      aria-label="싫어요"
                                      aria-pressed={dislikeActive}
                                      disabled={likeActive || isOwnComment}
                                      onClick={() =>
                                        handleToggleCommentReaction(
                                          personalReview.id,
                                          comment.id,
                                          "dislike"
                                        )
                                      }
                                    >
                                      <span
                                        className="review-reaction-icon is-dislike"
                                        aria-hidden="true"
                                      />
                                      {commentReactions[comment.id]?.dislikes ??
                                        comment.dislikes_count ??
                                        0}
                                    </button>
                                  </>
                                );
                              })()}
                            </div>
                          </div>
                          {commentEditing[comment.id] ? (
                            <div className="comment-edit-form">
                              <textarea
                                className="review-reply-input"
                                value={commentEditDrafts[comment.id] ?? comment.content}
                                onChange={(event) =>
                                  handleCommentEditChange(comment.id, event.target.value)
                                }
                              />
                              <div className="comment-edit-actions">
                                <button
                                  className="primary-btn review-reply-submit"
                                  type="button"
                                  onClick={() => handleCommentEditSave(personalReview.id, comment.id)}
                                >
                                  저장하기
                                </button>
                                <button
                                  className="ghost-btn review-link-btn"
                                  type="button"
                                  onClick={() => handleCommentEditCancel(comment.id)}
                                >
                                  취소
                                </button>
                              </div>
                            </div>
                          ) : (
                            <>
                              <p className="review-text">{comment.content}</p>
                              {currentUserPk &&
                                String(comment.user_id) === String(currentUserPk) && (
                                  <div className="comment-actions">
                                    <button
                                      className="ghost-btn comment-edit-btn"
                                      type="button"
                                      onClick={() =>
                                        handleCommentEditOpen(comment.id, comment.content)
                                      }
                                    >
                                      댓글 수정
                                    </button>
                                    <button
                                      className="ghost-btn comment-delete-btn"
                                      type="button"
                                      onClick={() =>
                                        handleCommentDelete(personalReview.id, comment.id)
                                      }
                                    >
                                      댓글 삭제
                                    </button>
                                  </div>
                                )}
                            </>
                          )}
                        </div>
                      ))
                    ) : (
                      <p className="muted">아직 댓글이 없습니다.</p>
                    )}
                    {commentErrors[personalReview.id] && (
                      <p className="muted">{commentErrors[personalReview.id]}</p>
                    )}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <article className="card review-card review-empty review-empty-stack">
              {myReviewOpen ? (
                <div className="review-form form-grid">
                  <div className="review-form-row review-form-row-full review-rating-actions-row" style={{ marginBottom: "0.5rem" }}>
                    <div className="review-rating-block">
                      <label>별점</label>
                      <div className="review-rating-input-wrap">
                        <div
                          id="my-review-rating"
                          className={`review-rating-input ${!isLoggedIn ? "is-disabled" : ""}`}
                          role="slider"
                          aria-label="별점"
                          aria-valuemin={0.5}
                          aria-valuemax={5}
                          aria-valuenow={previewReviewRating}
                          aria-valuetext={`${formatRatingLabel(previewReviewRating)}점`}
                          aria-disabled={!isLoggedIn}
                          tabIndex={isLoggedIn ? 0 : -1}
                          onKeyDown={handleReviewRatingKeyDown}
                          onMouseLeave={() => setHoverReviewRating(null)}
                        >
                          {Array.from({ length: 5 }, (_, index) => {
                            const starNumber = index + 1;
                            const fillPercent = getStarFillPercent(previewReviewRating, starNumber);

                            return (
                              <span
                                key={starNumber}
                                className={`review-rating-star-hitbox ${!isLoggedIn ? "is-disabled" : ""
                                  }`}
                                aria-label={`${starNumber}점`}
                                onMouseMove={(event) => handleReviewRatingHover(event, starNumber)}
                                onClick={(event) => handleReviewRatingSelect(event, starNumber)}
                              >
                                <span className="review-rating-star-image review-rating-star-empty" aria-hidden="true" />
                                <span
                                  className="review-rating-star-fill-wrap"
                                  aria-hidden="true"
                                  style={{ width: `${fillPercent}%` }}
                                >
                                  <span className="review-rating-star-image review-rating-star-filled" />
                                </span>
                              </span>
                            );
                          })}
                        </div>
                        <span className="review-rating-current">
                          {formatRatingLabel(previewReviewRating)}점
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="review-form-row review-form-row-full" style={{ marginTop: '0.5rem', marginBottom: '1rem' }}>
                    <label>감상 키워드 (필수)</label>
                    <ReviewKeywordSelector
                      selected={myReviewKeywords}
                      onChange={setMyReviewKeywords}
                      showErrors={showKeywordErrors}
                    />
                  </div>

                  <div className="review-form-row review-form-row-full">
                    <label htmlFor="my-review-content">리뷰 코멘트 (선택)</label>
                    <textarea
                      id="my-review-content"
                      className="review-reply-input"
                      placeholder={isLoggedIn ? "영화를 보며 느낀 점을 자유롭게 적어주세요." : ""}
                      value={myReviewContent}
                      maxLength={REVIEW_CONTENT_MAX_LENGTH}
                      readOnly={!isLoggedIn}
                      onChange={(event) =>
                        setMyReviewContent(
                          event.target.value.slice(0, REVIEW_CONTENT_MAX_LENGTH)
                        )
                      }
                    />
                    <p className="review-char-count" aria-live="polite">
                      {myReviewContent.length} / {REVIEW_CONTENT_MAX_LENGTH}
                    </p>
                    {!isLoggedIn && showReviewLoginMessage && (
                      <p className="error" key={`review-login-warning-${reviewLoginMessageTick}`}>
                        로그인 후 이용해주세요.
                      </p>
                    )}
                    {myReviewErrorMessage && (
                      <p className="error" role="alert">
                        {myReviewErrorMessage}
                      </p>
                    )}
                  </div>
                  <div className="review-form-row review-form-row-full review-rating-actions-row">
                    <div className="review-reply-actions review-form-actions" style={{ width: "100%", justifyContent: "flex-end" }}>
                      <div
                        className="group-select-wrap option-select review-visibility-wrap"
                        ref={visibilitySelectRef}
                      >
                        <button
                          type="button"
                          className="option-select-trigger"
                          aria-haspopup="listbox"
                          aria-expanded={isVisibilityOpen}
                          aria-controls="review-visibility-options"
                          disabled={!isLoggedIn}
                          onClick={() => setIsVisibilityOpen((prev) => !prev)}
                        >
                          <span>
                            {myReviewVisibility === "private" ? "비공개" : "공개"}
                          </span>
                          <span className="option-select-arrow" aria-hidden="true">
                            ▾
                          </span>
                        </button>
                        {isVisibilityOpen && isLoggedIn && (
                          <div
                            id="review-visibility-options"
                            className="search-results option-select-list"
                            role="listbox"
                          >
                            <button
                              type="button"
                              className="search-item option-select-item"
                              role="option"
                              aria-selected={myReviewVisibility === "public"}
                              onClick={() => {
                                setMyReviewVisibility("public");
                                setIsVisibilityOpen(false);
                              }}
                            >
                              <strong>공개</strong>
                              {myReviewVisibility === "public" && <span>✓</span>}
                            </button>
                            <button
                              type="button"
                              className="search-item option-select-item"
                              role="option"
                              aria-selected={myReviewVisibility === "private"}
                              onClick={() => {
                                setMyReviewVisibility("private");
                                setIsVisibilityOpen(false);
                              }}
                            >
                              <strong>비공개</strong>
                              {myReviewVisibility === "private" && <span>✓</span>}
                            </button>
                          </div>
                        )}
                      </div>
                      <button
                        className="primary-btn review-reply-submit"
                        type="button"
                        disabled={isSavingMyReview}
                        onClick={handleMyReviewSave}
                      >
                        {isSavingMyReview
                          ? isEditingMyReview
                            ? "수정 중..."
                            : "저장 중..."
                          : isEditingMyReview
                            ? "수정하기"
                            : "저장하기"}
                      </button>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="review-empty-row">
                  <p className="muted">아직 이 영화에는 리뷰를 작성하지 않았어요.</p>
                  <button
                    className="ghost-btn movie-detail-watch-btn is-active review-start-btn"
                    type="button"
                    onClick={() => {
                      setIsEditingMyReview(false);
                      setMyReviewRating(normalizeReviewRating(5));
                      setMyReviewKeywords([]);
                      setShowKeywordErrors(false);
                      setMyReviewContent("");
                      setMyReviewVisibility("public");
                      setMyReviewErrorMessage(null);
                      setMyReviewOpen(true);
                      setHoverReviewRating(null);
                      setIsVisibilityOpen(false);
                      setShowReviewLoginMessage(false);
                    }}
                  >
                    리뷰 남기기
                  </button>
                </div>
              )}
            </article>
          )}
        </section>

        <section className="section">
          <div className="section-header">
            <h2>다른 사람들의 리뷰</h2>
            <p>이 영화에 대한 다양한 반응</p>
          </div>
          {otherReviewsForDisplay.length === 0 ? (
            <article className="card review-card review-empty">
              <p className="muted">아직 이 영화에는 리뷰가 없어요.</p>
            </article>
          ) : (
            <div className="review-list">
              {otherReviewsForDisplay.map((review) => {
                const authorName = getDisplayAuthorName(review.user_id);
                const reviewVisibility = toReviewVisibility(review.is_public);
                const visibilityMeta = getReviewVisibilityMeta(reviewVisibility);
                const isPrivateReview = reviewVisibility === "private";
                const reviewContent = isPrivateReview
                  ? "비공개로 설정한 리뷰입니다"
                  : review.content ?? "리뷰 코멘트가 없습니다.";
                return (
                  <div className="review-item" key={review.id}>
                    <article className="card review-card">
                      <div className="review-header">
                        <div className="review-user">
                          <div className="review-avatar">
                            {authorName.substring(0, 2).toUpperCase()}
                          </div>
                          <div>
                            <p className="review-name" style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                              {authorName}
                              {reviewVisibility === "private" && (
                                <span
                                  className={`review-visibility-indicator ${visibilityMeta.className}`}
                                  role="img"
                                  aria-label={visibilityMeta.label}
                                  title={visibilityMeta.label}
                                />
                              )}
                            </p>
                            <div className="review-rating-mini" style={{ display: 'flex', alignItems: 'center', gap: '0.1rem', marginTop: '0.2rem' }}>
                              {Array.from({ length: 5 }, (_, i) => {
                                const isFilled = i < Math.floor(review.rating ?? 0);
                                const isHalf = !isFilled && i < (review.rating ?? 0);
                                return isHalf ? (
                                  <span key={i} style={{ position: 'relative', display: 'inline-block', fontSize: '1rem', lineHeight: 1 }}>
                                    <span style={{ color: '#cbd5e1' }}>★</span>
                                    <span style={{ position: 'absolute', top: 0, left: 0, width: '50%', overflow: 'hidden', color: '#fbbf24' }}>★</span>
                                  </span>
                                ) : (
                                  <span key={i} style={{ color: isFilled ? '#fbbf24' : '#cbd5e1', fontSize: '1rem', lineHeight: 1 }}>
                                    ★
                                  </span>
                                );
                              })}
                              <span style={{ fontSize: '0.85rem', color: '#64748b', marginLeft: '0.3rem' }}>
                                평점 {formatRatingLabel(review.rating)}
                              </span>
                            </div>
                          </div>
                        </div>
                        <div className="review-actions">
                          {(() => {
                            const reaction = myReviewReactions[review.id] ?? null;
                            const likeActive = reaction === "like";
                            const dislikeActive = reaction === "dislike";
                            return (
                              <>
                                <button
                                  className={`ghost-btn review-reaction-btn ${likeActive ? "is-active" : ""
                                    }`}
                                  type="button"
                                  aria-label="좋아요"
                                  aria-pressed={likeActive}
                                  disabled={dislikeActive}
                                  onClick={() => handleToggleReaction(review.id, "like")}
                                >
                                  <span
                                    className="review-reaction-icon"
                                    aria-hidden="true"
                                  />
                                  {reactions[review.id]?.likes ?? review.likes_count ?? 0}
                                </button>
                                {/* <span className="muted">|</span> */}
                                <button
                                  className={`ghost-btn review-reaction-btn ${dislikeActive ? "is-active" : ""
                                    }`}
                                  type="button"
                                  aria-label="싫어요"
                                  aria-pressed={dislikeActive}
                                  disabled={likeActive}
                                  onClick={() => handleToggleReaction(review.id, "dislike")}
                                >
                                  <span
                                    className="review-reaction-icon is-dislike"
                                    aria-hidden="true"
                                  />
                                  {reactions[review.id]?.dislikes ?? review.dislikes_count ?? 0}
                                </button>
                              </>
                            );
                          })()}
                        </div>
                      </div>
                      {(() => {
                        const keywords = (review as any).keywords as string[] | undefined;

                        // 기존 내용 (100자 자르기 포함)
                        const rawText = isPrivateReview
                          ? reviewContent
                          : reviewContent.length > 100
                            ? reviewContent.substring(0, 100) + "..."
                            : reviewContent;

                        return (
                          <>
                            {keywords && keywords.length > 0 && !isPrivateReview && (
                              <div className="review-keywords-badges" style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem', marginBottom: '0.5rem' }}>
                                {keywords.map((k) => (
                                  <span key={k} className="review-keyword-badge" style={{
                                    display: 'inline-flex',
                                    alignItems: 'center',
                                    padding: '0.25rem 0.6rem',
                                    backgroundColor: '#f8fafc',
                                    color: '#475569',
                                    borderRadius: '9999px',
                                    fontSize: '0.8rem',
                                    fontWeight: 500,
                                    border: '1px solid #e2e8f0'
                                  }}>
                                    #{getKeywordLabel(k)}
                                  </span>
                                ))}
                              </div>
                            )}
                            {(rawText !== "리뷰 코멘트가 없습니다." || !keywords?.length) && (
                              <p className="review-text">{rawText}</p>
                            )}
                          </>
                        );
                      })()}
                      {!isPrivateReview && (
                        <>
                          <div className="review-link-row" style={{ display: 'flex', alignItems: 'center', marginTop: '0.5rem' }}>
                            <button
                              className="ghost-btn review-link-btn"
                              type="button"
                              onClick={() => toggleCommentOpen(review.id)}
                            >
                              댓글({reviewComments[review.id]?.length ?? review.comments_count ?? 0})
                            </button>
                            <button
                              className="ghost-btn review-link-btn"
                              type="button"
                              onClick={() => toggleReplyOpen(review.id)}
                            >
                              댓글 달기
                            </button>
                            <div style={{ marginLeft: 'auto', fontSize: '0.8rem', color: '#94a3b8' }}>
                              {formatDateTime(review.created_at)}
                            </div>
                          </div>
                          {replyOpen[review.id] && (
                            <div className="review-reply-form">
                              <textarea
                                className="review-reply-input"
                                placeholder="댓글을 입력하세요"
                                value={replyDrafts[review.id] || ""}
                                onChange={(event) =>
                                  handleReplyChange(review.id, event.target.value)
                                }
                              />
                              <div className="review-reply-actions">
                                <button
                                  className="primary-btn review-reply-submit"
                                  type="button"
                                  onClick={() => handleReplySubmit(review.id)}
                                >
                                  저장하기
                                </button>
                              </div>
                            </div>
                          )}
                        </>
                      )
                      }
                    </article>
                    {!isPrivateReview && commentOpen[review.id] && (
                      <div className="comment-thread">
                        <div className="comment-list">
                          {commentLoading[review.id] ? (
                            <p className="muted">댓글을 불러오는 중...</p>
                          ) : (reviewComments[review.id] || []).length > 0 ? (
                            (reviewComments[review.id] || []).map((comment) => (
                              <div className="comment-card" key={comment.id}>
                                <div className="comment-meta">
                                  <span className="review-name">
                                    {getDisplayAuthorName(comment.user_id)}
                                  </span>
                                  <span className="muted">
                                    {formatDateTime(comment.created_at)}
                                  </span>
                                  <div className="comment-reactions">
                                    {(() => {
                                      const reaction = myCommentReactions[comment.id] ?? null;
                                      const likeActive = reaction === "like";
                                      const dislikeActive = reaction === "dislike";
                                      const isOwnComment =
                                        Boolean(currentUserPk) &&
                                        String(comment.user_id) === String(currentUserPk);
                                      return (
                                        <>
                                          <button
                                            className={`ghost-btn review-reaction-btn ${likeActive ? "is-active" : ""
                                              }`}
                                            type="button"
                                            aria-label="좋아요"
                                            aria-pressed={likeActive}
                                            disabled={dislikeActive || isOwnComment}
                                            onClick={() =>
                                              handleToggleCommentReaction(
                                                review.id,
                                                comment.id,
                                                "like"
                                              )
                                            }
                                          >
                                            <span
                                              className="review-reaction-icon"
                                              aria-hidden="true"
                                            />
                                            {commentReactions[comment.id]?.likes ??
                                              comment.likes_count ??
                                              0}
                                          </button>
                                          <button
                                            className={`ghost-btn review-reaction-btn ${dislikeActive ? "is-active" : ""
                                              }`}
                                            type="button"
                                            aria-label="싫어요"
                                            aria-pressed={dislikeActive}
                                            disabled={likeActive || isOwnComment}
                                            onClick={() =>
                                              handleToggleCommentReaction(
                                                review.id,
                                                comment.id,
                                                "dislike"
                                              )
                                            }
                                          >
                                            <span
                                              className="review-reaction-icon is-dislike"
                                              aria-hidden="true"
                                            />
                                            {commentReactions[comment.id]?.dislikes ??
                                              comment.dislikes_count ??
                                              0}
                                          </button>
                                        </>
                                      );
                                    })()}
                                  </div>
                                </div>
                                {commentEditing[comment.id] ? (
                                  <div className="comment-edit-form">
                                    <textarea
                                      className="review-reply-input"
                                      value={commentEditDrafts[comment.id] ?? comment.content}
                                      onChange={(event) =>
                                        handleCommentEditChange(comment.id, event.target.value)
                                      }
                                    />
                                    <div className="comment-edit-actions">
                                      <button
                                        className="primary-btn review-reply-submit"
                                        type="button"
                                        onClick={() => handleCommentEditSave(review.id, comment.id)}
                                      >
                                        저장하기
                                      </button>
                                      <button
                                        className="ghost-btn review-link-btn"
                                        type="button"
                                        onClick={() => handleCommentEditCancel(comment.id)}
                                      >
                                        취소
                                      </button>
                                    </div>
                                  </div>
                                ) : (
                                  <>
                                    <p className="review-text">{comment.content}</p>
                                    {currentUserPk &&
                                      String(comment.user_id) === String(currentUserPk) && (
                                        <div className="comment-actions">
                                          <button
                                            className="ghost-btn comment-edit-btn"
                                            type="button"
                                            onClick={() =>
                                              handleCommentEditOpen(comment.id, comment.content)
                                            }
                                          >
                                            댓글 수정
                                          </button>
                                          <button
                                            className="ghost-btn comment-delete-btn"
                                            type="button"
                                            onClick={() => handleCommentDelete(review.id, comment.id)}
                                          >
                                            댓글 삭제
                                          </button>
                                        </div>
                                      )}
                                  </>
                                )}
                              </div>
                            ))
                          ) : (
                            <p className="muted">아직 댓글이 없습니다.</p>
                          )}
                          {commentErrors[review.id] && (
                            <p className="muted">{commentErrors[review.id]}</p>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </section>

        {
          reviewDeleteConfirmOpen && (
            <div
              className="modal"
              role="dialog"
              aria-modal="true"
              aria-labelledby="review-delete-title"
            >
              <div
                className="modal-overlay"
                onClick={() => setReviewDeleteConfirmOpen(false)}
              />
              <div className="modal-content review-delete-modal">
                <div className="modal-header">
                  <h3 id="review-delete-title">리뷰 삭제</h3>
                </div>
                <p className="muted">삭제하시겠습니까?</p>
                <div className="modal-footer">
                  <button
                    className="secondary-btn"
                    type="button"
                    onClick={() => setReviewDeleteConfirmOpen(false)}
                  >
                    아니오
                  </button>
                  <button
                    className="primary-btn"
                    type="button"
                    disabled={isDeletingMyReview}
                    onClick={handleMyReviewDeleteConfirm}
                  >
                    {isDeletingMyReview ? "삭제 중..." : "예"}
                  </button>
                </div>
              </div>
            </div>
          )
        }
      </main >
    </MainLayout >
  );
}
















