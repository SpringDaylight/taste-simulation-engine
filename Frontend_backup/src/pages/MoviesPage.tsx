import { useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import MainLayout from "../components/layout/MainLayout";
import SectionHeader from "../components/common/SectionHeader";
import MovieTileCard from "../components/movie/MovieTileCard";
import LoadingState from "../components/common/LoadingState";
import EmptyState from "../components/common/EmptyState";
import { getMovies, type Movie } from "../api/A2_movies";
import {
  getCurrentUserWatchedMovies,
  saveCurrentUserWatchedMovie,
  deleteCurrentUserWatchedMovie,
} from "../api/A8_watched";
import { getAccessToken } from "../api/http";
import { setJsonToSession } from "../utils/storage";

const MOVIES_PAGE_SNAPSHOT_KEY = "mw_movies_page_snapshot";

type MoviesPageSnapshot = {
  searchQuery: string;
  selectedSorts: string[];
  selectedGenres: string[];
  selectedRuntime: string[];
  selectedYearRange: string[];
  appliedSorts: string[];
  appliedGenres: string[];
  appliedRuntime: string[];
  appliedYearRange: string[];
  appliedQuery: string;
  currentPage: number;
  scrollY: number;
  restoreOnReturn: boolean;
};

const sortFilters = [
  { value: "latest", label: "최신개봉순" },
  { value: "title", label: "가나다순" },
  { value: "popular", label: "리뷰많은순" },
  { value: "rating", label: "평점높은순" },
];

type GenreFilter = {
  value: string;
  label: string;
  queryGenres: string[];
};


type YearRangeFilter = {
  value: string;
  label: string;
  min: number;
  max?: number;
};
const genreFilters = [
  { value: "로맨스/로코", label: "로맨스/로코", queryGenres: ["로맨스"] },
  { value: "드라마/휴먼", label: "드라마/휴먼", queryGenres: ["드라마"] },
  {
    value: "스릴러/미스터리",
    label: "스릴러/미스터리",
    queryGenres: ["스릴러", "미스터리"],
  },
  { value: "공포/호러", label: "공포/호러", queryGenres: ["공포"] },
  { value: "액션", label: "액션", queryGenres: ["액션"] },
  { value: "범죄/느와르", label: "범죄/느와르", queryGenres: ["범죄"] },
  { value: "SF", label: "SF", queryGenres: ["SF"] },
  { value: "판타지", label: "판타지", queryGenres: ["판타지"] },
  { value: "코미디", label: "코미디", queryGenres: ["코미디"] },
  { value: "애니메이션", label: "애니메이션", queryGenres: ["애니메이션"] },
  { value: "역사/다큐", label: "역사/다큐", queryGenres: ["역사", "다큐멘터리"] },
] as const satisfies GenreFilter[];

const runtimeFilters = [
  { value: "under-100", label: "100분 이내" },
  { value: "between-100-120", label: "100~120분 이내" },
  { value: "between-120-140", label: "120~140분 이내" },
  { value: "over-140", label: "140분 이상" },
] as const;

const yearRangeFilters: YearRangeFilter[] = [
  { value: "pre1950", label: "1950년 이전", min: 0, max: 1949 },
  { value: "1950s", label: "1950년-1959년", min: 1950, max: 1959 },
  { value: "1960s", label: "1960년-1969년", min: 1960, max: 1969 },
  { value: "1970s", label: "1970년-1979년", min: 1970, max: 1979 },
  { value: "1980s", label: "1980년-1989년", min: 1980, max: 1989 },
  { value: "1990s", label: "1990년-1999년", min: 1990, max: 1999 },
  { value: "2000s", label: "2000년-2009년", min: 2000, max: 2009 },
  { value: "2010s", label: "2010년-2019년", min: 2010, max: 2019 },
  { value: "2020plus", label: "2020년 이후", min: 2020 },
];


const resolveFilterToGenres = (values: string[]) => {
  return Array.from(
    new Set(
      values.flatMap((value) => {
        const matched = genreFilters.find((filter) => filter.value === value);
        return matched ? matched.queryGenres : [value];
      })
    )
  );
};

const resolveGenresToFilterValues = (genres: string[]) => {
  return genreFilters
    .filter((filter) => filter.queryGenres.some((genre) => genres.includes(genre)))
    .map((filter) => filter.value);
};

const parseCsvParam = (value: string | null) =>
  value
    ? value
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean)
    : [];

const resolveRuntimeRange = (value: string | null): {
  runtime_min?: number;
  runtime_max?: number;
} => {
  if (!value) return {};
  switch (value) {
    case "under-100":
      return { runtime_max: 100 };
    case "between-100-120":
      return { runtime_min: 100, runtime_max: 120 };
    case "between-120-140":
      return { runtime_min: 120, runtime_max: 140 };
    case "over-140":
      return { runtime_min: 140 };
    default:
      return {};
  }
};

const resolveYearRange = (value: string | null): {
  year_min?: number;
  year_max?: number;
} => {
  if (!value) return {};
  const range = yearRangeFilters.find((filter) => filter.value === value);
  if (!range) return {};
  return {
    year_min: range.min,
    ...(typeof range.max === "number" ? { year_max: range.max } : {}),
  };
};


export default function MoviesPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const isLoggedIn = Boolean(getAccessToken());
  const [movies, setMovies] = useState<Movie[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedSorts, setSelectedSorts] = useState<string[]>([]);
  const [selectedGenres, setSelectedGenres] = useState<string[]>([]);
  const [selectedRuntime, setSelectedRuntime] = useState<string[]>([]);
  const [selectedYearRange, setSelectedYearRange] = useState<string[]>([]);
  const [appliedSorts, setAppliedSorts] = useState<string[]>([]);
  const [appliedGenres, setAppliedGenres] = useState<string[]>([]);
  const [appliedRuntime, setAppliedRuntime] = useState<string[]>([]);
  const [appliedYearRange, setAppliedYearRange] = useState<string[]>([]);
  const [appliedQuery, setAppliedQuery] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [pendingScrollRestore, setPendingScrollRestore] = useState<number | null>(
    null
  );
  const [watchedMovieIds, setWatchedMovieIds] = useState<Set<number>>(
    () => new Set()
  );
  const shouldSkipSearchParamInitRef = useRef(false);
  const skipUrlSyncRef = useRef(false);

  useEffect(() => {
    if (!isLoggedIn) {
      setWatchedMovieIds(new Set());
      return;
    }

    let isCancelled = false;

    const fetchWatchedMovies = async () => {
      try {
        console.log('🔍 [MoviesPage] Fetching watched movies...');
        const response = await getCurrentUserWatchedMovies({
          page: 1,
          page_size: 100,
        });
        if (isCancelled) return;
        
        console.log('✅ [MoviesPage] Watched movies response:', response);
        console.log('   Total watched:', response.total);
        console.log('   Items count:', response.items.length);
        
        const movieIds = response.items.map((item) => Number(item.movie_id)).filter(
          (id) => Number.isFinite(id)
        );
        
        console.log('   Movie IDs:', movieIds);
        
        setWatchedMovieIds(new Set(movieIds));
        console.log('✅ [MoviesPage] Watched movie IDs set:', movieIds.length);
      } catch (err) {
        if (isCancelled) return;
        console.error('❌ [MoviesPage] Failed to fetch watched movies:', err);
        setWatchedMovieIds(new Set());
      }
    };

    fetchWatchedMovies();
    return () => {
      isCancelled = true;
    };
  }, [isLoggedIn]);

  useEffect(() => {
    if (shouldSkipSearchParamInitRef.current) {
      shouldSkipSearchParamInitRef.current = false;
      return;
    }

    const queryFromUrl = searchParams.get("query");
    const genresFromUrl = parseCsvParam(searchParams.get("genres"));
    const runtimeFromUrl = parseCsvParam(searchParams.get("runtime"));
    const yearsFromUrl = parseCsvParam(searchParams.get("years"));
    const sortFromUrl = searchParams.get("sort");
    const pageFromUrl = Number(searchParams.get("page"));

    const hasAnyParam =
      Boolean(queryFromUrl) ||
      genresFromUrl.length > 0 ||
      runtimeFromUrl.length > 0 ||
      yearsFromUrl.length > 0 ||
      Boolean(sortFromUrl) ||
      Number.isFinite(pageFromUrl);

    if (!hasAnyParam) return;

    skipUrlSyncRef.current = true;

    if (queryFromUrl) {
      setSearchQuery(queryFromUrl);
      setAppliedQuery(queryFromUrl);
    }

    if (genresFromUrl.length > 0) {
      const selectedFilterValues = resolveGenresToFilterValues(genresFromUrl);
      setSelectedGenres(selectedFilterValues.length > 0 ? selectedFilterValues : genresFromUrl);
      setAppliedGenres(genresFromUrl);
    }

    if (runtimeFromUrl.length > 0) {
      setSelectedRuntime(runtimeFromUrl);
      setAppliedRuntime(runtimeFromUrl);
    }

    if (yearsFromUrl.length > 0) {
      setSelectedYearRange(yearsFromUrl);
      setAppliedYearRange(yearsFromUrl);
    }

    if (sortFromUrl) {
      setSelectedSorts([sortFromUrl]);
      setAppliedSorts([sortFromUrl]);
    }

    if (Number.isFinite(pageFromUrl) && pageFromUrl > 0) {
      setCurrentPage(pageFromUrl);
    } else {
      setCurrentPage(1);
    }
  }, [searchParams]);

  useEffect(() => {
    if (skipUrlSyncRef.current) {
      skipUrlSyncRef.current = false;
      return;
    }

    const params = new URLSearchParams();
    const trimmedQuery = appliedQuery.trim();

    if (trimmedQuery) {
      params.set("query", trimmedQuery);
    }

    if (appliedGenres.length > 0) {
      params.set("genres", appliedGenres.join(","));
    }

    if (appliedRuntime.length > 0) {
      params.set("runtime", appliedRuntime.join(","));
    }

    if (appliedYearRange.length > 0) {
      params.set("years", appliedYearRange.join(","));
    }

    if (appliedSorts.length > 0) {
      params.set("sort", appliedSorts[0]);
    }

    if (currentPage > 1) {
      params.set("page", String(currentPage));
    }

    const nextQuery = params.toString();
    if (nextQuery === searchParams.toString()) return;

    shouldSkipSearchParamInitRef.current = true;
    setSearchParams(params, { replace: true });
  }, [
    appliedQuery,
    appliedGenres,
    appliedRuntime,
    appliedYearRange,
    appliedSorts,
    currentPage,
    searchParams,
    setSearchParams,
  ]);
  useEffect(() => {
    if (pendingScrollRestore === null) return;
    if (loading) return;

    const frame = window.requestAnimationFrame(() => {
      window.scrollTo({
        top: pendingScrollRestore,
        behavior: "auto",
      });
      setPendingScrollRestore(null);
    });

    return () => window.cancelAnimationFrame(frame);
  }, [loading, pendingScrollRestore, movies.length]);

  useEffect(() => {
    let isCancelled = false;

    const fetchMovies = async () => {
      setLoading(true);
      setError(null);
      try {
        const sortKey = appliedSorts.length > 0 ? appliedSorts[0] : undefined;
        const sort = sortKey
          ? (sortKey as "latest" | "popular" | "rating" | "title")
          : undefined;
        const genres = appliedGenres.length > 0 ? appliedGenres.join(",") : undefined;
        const runtimeRange =
          appliedRuntime.length === 1
            ? resolveRuntimeRange(appliedRuntime[0])
            : {};
        const yearRange =
          appliedYearRange.length === 1
            ? resolveYearRange(appliedYearRange[0])
            : {};
        const runtimeRangesParam =
          appliedRuntime.length > 1 ? appliedRuntime.join(",") : undefined;
        const yearRangesParam =
          appliedYearRange.length > 1 ? appliedYearRange.join(",") : undefined;

        const response = await getMovies({
          query: appliedQuery || undefined,
          genres,
          sort,
          runtime_ranges: runtimeRangesParam,
          ...runtimeRange,
          year_ranges: yearRangesParam,
          ...yearRange,
          page: currentPage,
          page_size: 20,
        });

        if (isCancelled) return;
        const normalizedQuery = appliedQuery.trim().toLowerCase();
        const filteredByTitle =
          normalizedQuery.length > 0
            ? response.movies.filter((movie) =>
                (movie.title ?? "").toLowerCase().includes(normalizedQuery)
              )
            : response.movies;
        setMovies(filteredByTitle);
        const nextTotalPages = Math.max(1, Math.ceil(response.total / response.page_size));
        setTotalPages(nextTotalPages);
      } catch (err) {
        if (isCancelled) return;
        setError("영화 목록을 불러오는데 실패했습니다.");
        console.error("Failed to fetch movies:", err);
      } finally {
        if (isCancelled) return;
        setLoading(false);
      }
    };

    fetchMovies();
    return () => {
      isCancelled = true;
    };
  }, [
    appliedSorts,
    appliedGenres,
    appliedQuery,
    appliedRuntime,
    appliedYearRange,
    currentPage,
  ]);
const handleSortSelect = (value: string) => {
    setSelectedSorts((prev) => {
      const nextSorts = prev[0] === value ? [] : [value];
      setAppliedSorts(nextSorts);
      setCurrentPage(1);
      return nextSorts;
    });
  };

  const handleGenreToggle = (value: string) => {
    setSelectedGenres((prev) => {
      const nextSelected = prev.includes(value)
        ? prev.filter((item) => item !== value)
        : [...prev, value];
      setAppliedGenres(resolveFilterToGenres(nextSelected));
      setCurrentPage(1);
      return nextSelected;
    });
  };

  const handleRuntimeToggle = (value: string) => {
    setSelectedRuntime((prev) => {
      const nextSelected = prev.includes(value)
        ? prev.filter((item) => item !== value)
        : [...prev, value];
      setAppliedRuntime(nextSelected);
      setCurrentPage(1);
      return nextSelected;
    });
  };

  const handleYearRangeToggle = (value: string) => {
    setSelectedYearRange((prev) => {
      const nextSelected = prev.includes(value)
        ? prev.filter((item) => item !== value)
        : [...prev, value];
      setAppliedYearRange(nextSelected);
      setCurrentPage(1);
      return nextSelected;
    });
  };

  const handleApplyFilters = () => {
    setAppliedQuery(searchQuery);
    setCurrentPage(1);
  };

  const handleMarkWatched = async (movie: Movie) => {
    if (!isLoggedIn) {
      navigate("/login");
      return;
    }

    const isWatched = watchedMovieIds.has(movie.id);
    console.log('🔄 [MoviesPage] Toggling watched status:', {
      movieId: movie.id,
      movieTitle: movie.title,
      currentStatus: isWatched ? 'watched' : 'not watched',
      action: isWatched ? 'remove' : 'add'
    });

    try {
      if (isWatched) {
        // 이미 시청함 → 제거
        console.log('   Calling deleteCurrentUserWatchedMovie...');
        await deleteCurrentUserWatchedMovie(movie.id);
        setWatchedMovieIds((prev) => {
          const next = new Set(prev);
          next.delete(movie.id);
          console.log('   ✅ Removed from watched, new count:', next.size);
          return next;
        });
      } else {
        // 시청 안 함 → 추가
        console.log('   Calling saveCurrentUserWatchedMovie...');
        await saveCurrentUserWatchedMovie({ movie_id: movie.id });
        setWatchedMovieIds((prev) => {
          const next = new Set(prev);
          next.add(movie.id);
          console.log('   ✅ Added to watched, new count:', next.size);
          return next;
        });
      }
    } catch (err) {
      console.error("❌ Failed to toggle watched movie:", err);
    }
  };

  const saveSnapshot = (restoreOnReturn: boolean) => {
    const snapshot: MoviesPageSnapshot = {
      searchQuery,
      selectedSorts,
      selectedGenres,
      selectedRuntime,
      selectedYearRange,
      appliedSorts,
      appliedGenres,
      appliedRuntime,
      appliedYearRange,
      appliedQuery,
      currentPage,
      scrollY: window.scrollY,
      restoreOnReturn,
    };
    setJsonToSession(MOVIES_PAGE_SNAPSHOT_KEY, snapshot);
  };

  const handleOpenMovieDetail = (movieId: number) => {
    saveSnapshot(true);
    navigate(`/movies/${movieId}`);
  };

  const pageWindow = (() => {
    const windowSize = 5;
    let start = Math.max(1, currentPage - 2);
    let end = Math.min(totalPages, currentPage + 2);

    if (currentPage <= 3) {
      end = Math.min(totalPages, windowSize);
    }

    if (currentPage >= totalPages - 2) {
      start = Math.max(1, totalPages - (windowSize - 1));
    }

    return { start, end };
  })();

  return (
    <MainLayout>
      <main className="container movies-page">
        {/* <section className="page-title">
          <h1>영화 검색하기</h1>
        </section> */}

        <section className="section card">
          {/* <div className="section-header">
            <p>장르와 분위기에 따라 원하는 기준으로 골라보세요</p>
          </div> */}
          <div className="section-search">
            <div className="hero-actions">
              <input
                className="search-input"
                type="text"
                placeholder="영화 제목을 검색해보세요"
                value={searchQuery}
                onChange={(event) => setSearchQuery(event.target.value)}
              />
              <button
                className="primary-btn"
                type="button"
                onClick={handleApplyFilters}
              >
                검색
              </button>
            </div>
          </div>

          <div className="filter-group movie-filter-group filter-table">
            <div className="filter-box-header">
              <span className="filter-box-icon" aria-hidden="true" />
              <span className="filter-box-title">영화 필터</span>
            </div>
            <div className="filter-row">
              <p className="filter-title">장르</p>
              <div className="filter-options">
                {genreFilters.map((filter) => (
                  <button
                    key={filter.value}
                    className={`filter-chip ${
                      selectedGenres.includes(filter.value) ? "active" : ""
                    }`}
                    type="button"
                    onClick={() => handleGenreToggle(filter.value)}
                  >
                    {filter.label}
                  </button>
                ))}
              </div>
            </div>
            <div className="filter-row">
              <p className="filter-title">개봉년도</p>
              <div className="filter-options">
                {yearRangeFilters.map((filter) => (
                  <button
                    key={filter.value}
                    className={`filter-chip ${
                      selectedYearRange.includes(filter.value) ? "active" : ""
                    }`}
                    type="button"
                    onClick={() => handleYearRangeToggle(filter.value)}
                  >
                    {filter.label}
                  </button>
                ))}
              </div>
            </div>
            <div className="filter-row">
              <p className="filter-title">상영시간</p>
              <div className="filter-options">
                {runtimeFilters.map((filter) => (
                  <button
                    key={filter.value}
                    className={`filter-chip ${
                      selectedRuntime.includes(filter.value) ? "active" : ""
                    }`}
                    type="button"
                    onClick={() => handleRuntimeToggle(filter.value)}
                  >
                    {filter.label}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section className="section">
          <SectionHeader title="검색결과" />
          <div className="movie-sort-links">
            {sortFilters.map((filter) => (
              <button
                key={filter.value}
                className={`movie-sort-link ${
                  selectedSorts.includes(filter.value) ? "active" : ""
                }`}
                type="button"
                onClick={() => handleSortSelect(filter.value)}
                aria-pressed={selectedSorts.includes(filter.value)}
              >
                {filter.label}
              </button>
            ))}
          </div>

          {loading && <LoadingState />}
          {error && <p className="error">{error}</p>}

          {!loading && !error && movies.length === 0 && (
            <EmptyState message="검색결과가 없습니다." />
          )}

          {!loading && !error && movies.length > 0 && (
            <div className="movie-grid">
              {movies.map((movie) => (
                <MovieTileCard
                  key={movie.id}
                  className="movie-card-clickable"
                  title={movie.title}
                  posterUrl={
                    movie.poster_url ||
                    "https://via.placeholder.com/500x750?text=No+Image"
                  }
                  role="button"
                  tabIndex={0}
                  onClick={() => handleOpenMovieDetail(movie.id)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      handleOpenMovieDetail(movie.id);
                    }
                  }}
                  titleSlot={
                    <div className="movie-card-title-row">
                      <h3>{movie.title}</h3>
                      <button
                        className={`ghost-btn movie-detail-watch-btn ${
                          watchedMovieIds.has(movie.id) ? "is-active" : ""
                        }`}
                        type="button"
                        aria-pressed={watchedMovieIds.has(movie.id)}
                        onClick={(event) => {
                          event.preventDefault();
                          event.stopPropagation();
                          console.log('🔘 [MoviesPage] Watch button clicked:', {
                            movieId: movie.id,
                            movieTitle: movie.title,
                            isWatched: watchedMovieIds.has(movie.id),
                            allWatchedIds: Array.from(watchedMovieIds)
                          });
                          handleMarkWatched(movie);
                        }}
                      >
                        시청함
                      </button>
                    </div>
                  }
                >
                  <p className="movie-rating">
                    평점{" "}
                    {typeof movie.avg_rating === "number"
                      ? movie.avg_rating.toFixed(1)
                      : "정보 없음"}{" "}
                    ({movie.reviews_count ?? movie.review_count ?? 0})
                  </p>
                  <p className="muted synopsis-clamp">
                    {movie.synopsis || "줄거리 정보가 없습니다."}
                  </p>
                </MovieTileCard>
              ))}
            </div>
          )}

          {!loading && !error && totalPages > 1 && (
            <div className="pagination">
              <button
                className="page-btn"
                type="button"
                onClick={() => setCurrentPage((page) => Math.max(1, page - 1))}
                disabled={currentPage === 1}
              >
                Prev
              </button>

              {pageWindow.start > 1 && (
                <>
                  <button
                    className="page-btn"
                    type="button"
                    onClick={() => setCurrentPage(1)}
                  >
                    1
                  </button>
                  <span className="pagination-ellipsis">...</span>
                </>
              )}

              {Array.from(
                { length: pageWindow.end - pageWindow.start + 1 },
                (_, index) => pageWindow.start + index
              ).map((page) => (
                <button
                  key={page}
                  className={`page-btn ${page === currentPage ? "active" : ""}`}
                  type="button"
                  onClick={() => setCurrentPage(page)}
                >
                  {page}
                </button>
              ))}

              {pageWindow.end < totalPages && (
                <>
                  <span className="pagination-ellipsis">...</span>
                  <button
                    className="page-btn"
                    type="button"
                    onClick={() => setCurrentPage(totalPages)}
                  >
                    {totalPages}
                  </button>
                </>
              )}

              <button
                className="page-btn"
                type="button"
                onClick={() =>
                  setCurrentPage((page) => Math.min(totalPages, page + 1))
                }
                disabled={currentPage === totalPages}
              >
                Next
              </button>
            </div>
          )}
        </section>
      </main>
    </MainLayout>
  );
}









