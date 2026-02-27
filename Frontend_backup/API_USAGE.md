# Frontend API Usage Guide

## 설정

### 1. 환경변수 설정
`.env` 파일에서 API URL 설정:
```env
VITE_API_BASE_URL=http://localhost:8000
```

### 2. API Import
```typescript
// 전체 API 가져오기
import api from '@/api';

// 또는 개별 함수 가져오기
import { getMovies, getMovie } from '@/api/A2_movies';
import { getCurrentUser } from '@/api/A7_profile';
```

---

## Movies API 사용법

### 영화 목록 조회
```typescript
import { getMovies } from '@/api/A2_movies';

// 기본 목록
const response = await getMovies();

// 검색
const searchResult = await getMovies({
  query: '아바타',
  page: 1,
  page_size: 20
});

// 장르 필터
const actionMovies = await getMovies({
  genres: '액션',
  sort: 'popular',
  page: 1
});

// 여러 장르
const multiGenre = await getMovies({
  genres: '액션,드라마',
  sort: 'rating'
});
```

### 영화 상세 조회
```typescript
import { getMovie } from '@/api/A2_movies';

const movie = await getMovie(1168190);
console.log(movie.title); // "더 레킹 크루"
console.log(movie.genres); // ["액션", "코미디", "범죄"]
```

### 영화별 리뷰 조회
```typescript
import { getMovieReviews } from '@/api/A2_movies';

const reviews = await getMovieReviews(1168190, {
  page: 1,
  page_size: 10
});

console.log(reviews.total); // 전체 리뷰 수
console.log(reviews.reviews); // 리뷰 배열
```

### 리뷰 작성
```typescript
import { createMovieReview } from '@/api/A2_movies';

const newReview = await createMovieReview(
  1168190, // movieId
  'user001', // userId
  {
    rating: 4.5,
    content: '정말 재미있었습니다!'
  }
);
```

### 편의 함수들
```typescript
import {
  searchMovies,
  getMoviesByGenre,
  getPopularMovies,
  getLatestMovies
} from '@/api/A2_movies';

// 검색
const searchResult = await searchMovies('주토피아', 1);

// 장르별
const actionMovies = await getMoviesByGenre('액션', 'popular', 1);

// 인기 영화
const popular = await getPopularMovies(1);

// 최신 영화
const latest = await getLatestMovies(1);
```

---

## Reviews API 사용법

### 리뷰 상세 조회
```typescript
import { getReview } from '@/api/A6_reviews';

const review = await getReview(1);
console.log(review.rating); // 4.5
console.log(review.likes_count); // 5
```

### 리뷰 수정
```typescript
import { updateReview } from '@/api/A6_reviews';

const updated = await updateReview(1, {
  rating: 5.0,
  content: '다시 봐도 최고입니다!'
});
```

### 리뷰 삭제
```typescript
import { deleteReview } from '@/api/A6_reviews';

await deleteReview(1);
```

### 좋아요/싫어요
```typescript
import { likeReview, dislikeReview, toggleReviewLike } from '@/api/A6_reviews';

// 좋아요
await likeReview(1, 'user001');

// 싫어요
await dislikeReview(1, 'user001');

// 토글 (직접 제어)
await toggleReviewLike(1, 'user001', true); // 좋아요
await toggleReviewLike(1, 'user001', false); // 싫어요
```

### 댓글 조회
```typescript
import { getReviewComments } from '@/api/A6_reviews';

const comments = await getReviewComments(1, {
  skip: 0,
  limit: 50
});

comments.forEach(comment => {
  console.log(comment.content);
});
```

### 댓글 작성
```typescript
import { createReviewComment } from '@/api/A6_reviews';

const newComment = await createReviewComment(
  1, // reviewId
  'user001', // userId
  {
    content: '저도 같은 생각이에요!'
  }
);
```

---

## Profile/User API 사용법

### 내 정보 조회
```typescript
import { getCurrentUser } from '@/api/A7_profile';

const user = await getCurrentUser('user001');
console.log(user.name); // "김영화"
console.log(user.avatar_text); // "따뜻한 드라마"
```

### 사용자 생성
```typescript
import { createUser } from '@/api/A7_profile';

const newUser = await createUser({
  id: 'user011',
  name: '새사용자',
  avatar_text: '영화 애호가'
});
```

### 사용자 정보 수정
```typescript
import { updateCurrentUser } from '@/api/A7_profile';

const updated = await updateCurrentUser('user001', {
  name: '김영화2',
  avatar_text: '액션 영화 팬'
});
```

### 내 리뷰 목록
```typescript
import { getCurrentUserReviews } from '@/api/A7_profile';

const myReviews = await getCurrentUserReviews('user001', {
  page: 1,
  page_size: 20
});

console.log(myReviews.total); // 전체 리뷰 수
myReviews.reviews.forEach(review => {
  console.log(`${review.movie_id}: ${review.rating}점`);
});
```

### 취향 분석 조회
```typescript
import { getUserTasteAnalysis } from '@/api/A7_profile';

const taste = await getUserTasteAnalysis('user001');
console.log(taste.summary_text);
// "당신은 감성적이고 따뜻한 이야기를 선호하시는군요..."
```

---

## React Component 예제

### 영화 목록 컴포넌트
```typescript
import { useState, useEffect } from 'react';
import { getMovies, type Movie } from '@/api/A2_movies';

function MovieList() {
  const [movies, setMovies] = useState<Movie[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchMovies() {
      try {
        const response = await getMovies({ sort: 'popular', page: 1 });
        setMovies(response.movies);
      } catch (error) {
        console.error('Failed to fetch movies:', error);
      } finally {
        setLoading(false);
      }
    }

    fetchMovies();
  }, []);

  if (loading) return <div>Loading...</div>;

  return (
    <div>
      {movies.map(movie => (
        <div key={movie.id}>
          <h3>{movie.title}</h3>
          <p>{movie.genres.join(', ')}</p>
        </div>
      ))}
    </div>
  );
}
```

### 리뷰 작성 컴포넌트
```typescript
import { useState } from 'react';
import { createMovieReview } from '@/api/A2_movies';

function ReviewForm({ movieId, userId }: { movieId: number; userId: string }) {
  const [rating, setRating] = useState(5);
  const [content, setContent] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);

    try {
      await createMovieReview(movieId, userId, { rating, content });
      alert('리뷰가 작성되었습니다!');
      setContent('');
    } catch (error) {
      alert('리뷰 작성에 실패했습니다.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <select value={rating} onChange={e => setRating(Number(e.target.value))}>
        <option value={5}>5점</option>
        <option value={4.5}>4.5점</option>
        <option value={4}>4점</option>
        <option value={3.5}>3.5점</option>
        <option value={3}>3점</option>
      </select>
      <textarea
        value={content}
        onChange={e => setContent(e.target.value)}
        placeholder="리뷰를 작성하세요"
      />
      <button type="submit" disabled={submitting}>
        {submitting ? '작성 중...' : '리뷰 작성'}
      </button>
    </form>
  );
}
```

### 좋아요 버튼 컴포넌트
```typescript
import { useState } from 'react';
import { likeReview } from '@/api/A6_reviews';

function LikeButton({ reviewId, userId, initialCount }: {
  reviewId: number;
  userId: string;
  initialCount: number;
}) {
  const [liked, setLiked] = useState(false);
  const [count, setCount] = useState(initialCount);

  const handleLike = async () => {
    try {
      await likeReview(reviewId, userId);
      setLiked(!liked);
      setCount(liked ? count - 1 : count + 1);
    } catch (error) {
      console.error('Failed to like review:', error);
    }
  };

  return (
    <button onClick={handleLike}>
      {liked ? '❤️' : '🤍'} {count}
    </button>
  );
}
```

---

## 에러 처리

### Try-Catch 패턴
```typescript
import { getMovie } from '@/api/A2_movies';

async function fetchMovie(id: number) {
  try {
    const movie = await getMovie(id);
    return movie;
  } catch (error) {
    if (error instanceof Error) {
      console.error('Error:', error.message);
      // 사용자에게 에러 메시지 표시
      alert(`영화를 불러올 수 없습니다: ${error.message}`);
    }
    return null;
  }
}
```

### React Query 사용 (권장)
```typescript
import { useQuery } from '@tanstack/react-query';
import { getMovies } from '@/api/A2_movies';

function MovieList() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['movies', 'popular'],
    queryFn: () => getMovies({ sort: 'popular' })
  });

  if (isLoading) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;

  return (
    <div>
      {data?.movies.map(movie => (
        <div key={movie.id}>{movie.title}</div>
      ))}
    </div>
  );
}
```

---

## 테스트용 데이터

### 사용 가능한 사용자 ID
- user001, user002, user003, ..., user010

### 영화 ID 예시
- 1168190 (더 레킹 크루)
- 1084242 (주토피아 2)
- 19995 (아바타)
- 278 (쇼생크 탈출)

### 장르 목록
- 액션, 모험, 드라마, 스릴러, SF, 코미디, 판타지, 범죄, 공포, 가족

---

## 주의사항

1. **사용자 ID**: 모든 API 호출 시 `user_id`가 필요합니다. 실제 인증 시스템 구현 전까지는 테스트 ID를 사용하세요.

2. **CORS**: 백엔드 서버가 `http://localhost:8000`에서 실행 중이어야 합니다.

3. **에러 처리**: 모든 API 호출은 try-catch로 감싸서 에러를 처리하세요.

4. **타입 안정성**: TypeScript 타입이 정의되어 있으므로 IDE의 자동완성을 활용하세요.

5. **페이지네이션**: 대부분의 목록 API는 페이지네이션을 지원합니다. `page`와 `page_size` 파라미터를 활용하세요.
