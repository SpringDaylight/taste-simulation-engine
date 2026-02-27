# 리뷰 기반 취향 업데이트 파이프라인

## 개요
이 문서는 리뷰 제출을 기반으로 사용자 취향과 영화 벡터를 업데이트하는 전체 파이프라인을 설명합니다.

## 파이프라인 흐름

```
[1] 사용자가 리뷰 작성 (평점 + 선택적 텍스트)
         ↓
[2] 리뷰가 데이터베이스에 저장
         ↓
[3] 취향 업데이트 트리거
         ↓
[4] 사용자 취향 벡터 업데이트
[5] 영화 벡터 업데이트 (리뷰 텍스트가 있는 경우)
         ↓
[6] 캐시 무효화 (향후: 추천 목록)
         ↓
[7] 다음 추천에 업데이트된 취향 반영
```

## 구현 세부사항

### 1. 백엔드 서비스: `PreferenceUpdater`

**위치**: `services/preference_updater.py`

**주요 메서드**:
- `update_from_review()`: 리뷰 기반 업데이트의 메인 진입점
- `_analyze_review_text()`: LLM 기반 리뷰 텍스트 분석
- `_calculate_rating_weight()`: 평점을 선호도 가중치로 변환
- `_update_user_preference()`: 사용자 취향 벡터 업데이트
- `_update_movie_vector()`: 영화 특성 벡터 업데이트

**평점 가중치 공식**:
```python
rating_weight = (rating - 3.0) / 2.0

# 예시:
# 5.0 → +1.0 (강한 선호)
# 4.0 → +0.5 (보통 선호)
# 3.0 →  0.0 (중립)
# 2.0 → -0.5 (보통 비선호)
# 0.5 → -1.0 (강한 비선호)
```

**벡터 업데이트 공식**:
```python
new_value = current_value + learning_rate * weight * (target_value - current_value)

# 긍정적 리뷰 (weight > 0):
#   영화의 특성 방향으로 이동
# 부정적 리뷰 (weight < 0):
#   영화의 특성 반대 방향으로 이동
```

**학습률**:
- 사용자 취향: 0.15 (기본값, 조정 가능)
- 영화 벡터: 0.05 (안정성 유지를 위해 느린 변화)

### 2. API 엔드포인트

**위치**: `api/user_preferences.py`

**엔드포인트**: `POST /user-preferences/{user_id}/update-from-review`

**파라미터**:
- `user_id` (경로): 사용자 식별자
- `movie_id` (쿼리): 영화 ID
- `rating` (쿼리): 리뷰 평점 (0.5-5.0)
- `learning_rate` (쿼리, 선택): 학습률 (기본값: 0.15)

**응답**:
```json
{
  "success": true,
  "message": "User preference and movie vector updated based on review",
  "user_id": "user_123",
  "movie_id": 389,
  "rating": 5.0,
  "rating_weight": 1.0,
  "review_analyzed": false,
  "movie_vector_updated": false,
  "updated_at": "2026-02-18T12:34:56"
}
```

### 3. 프론트엔드 통합

**위치**: `src/pages/MovieDetailPage.tsx`

**통합 지점**: `handleMyReviewSave()` 함수에서 리뷰 제출 후

```typescript
// 리뷰 저장 후
try {
  const { updatePreferenceFromReview } = await import("../api/userPreferences");
  await updatePreferenceFromReview(
    userPk,
    movie.id,
    reviewPayload.rating
  );
  console.log("User preference updated based on review");
} catch (prefError) {
  console.warn("Failed to update preference from review:", prefError);
  // 취향 업데이트 실패해도 리뷰는 저장됨
}
```

**API 클라이언트**: `src/api/userPreferences.ts`

```typescript
export function updatePreferenceFromReview(
  userId: string,
  movieId: number,
  rating: number,
  learningRate: number = 0.15
): Promise<{ success: boolean; message: string; updated_at: string }>
```

## 업데이트되는 항목

### 사용자 취향 벡터

**업데이트되는 필드**:
- `emotion_scores`: 감정 톤 선호도
- `narrative_traits`: 스토리 구조 선호도
- `direction_mood`: 페이싱 및 분위기 선호도
- `character_relationship`: 캐릭터 관계 선호도
- `ending_preference`: 엔딩 유형 선호도

**태그 관리**:
- 높은 평점 (≥4.0): 영화의 주요 태그를 `boost_tags`에 추가
- 낮은 평점 (≤2.0): 영화의 주요 태그를 `dislike_tags`에 추가
- 태그는 boost 20개, dislike 15개로 제한

### 영화 벡터

**업데이트 조건**: 리뷰 텍스트가 제공된 경우에만

**업데이트되는 필드**:
- `emotion_scores`: 사용자의 감정 반응 기반 조정
- `narrative_traits`: 사용자의 서사 인식 기반 조정
- `ending_preference`: 사용자의 엔딩 반응 기반 조정

**업데이트 전략**:
- 긍정적 리뷰 (≥4.0): 리뷰 분석 방향으로 이동 (가중치 1.0)
- 중립적 리뷰 (2.0-4.0): 중간 정도 조정 (가중치 0.6)
- 부정적 리뷰 (≤2.0): 최소 조정 (가중치 0.3)

## 에러 처리

**시나리오**:
1. 사용자 취향을 찾을 수 없음 → 400 에러, 취향 설문 완료 안내
2. 영화 벡터를 찾을 수 없음 → 400 에러, 업데이트 불가
3. 리뷰 텍스트 분석 실패 → 영화 벡터만으로 계속 진행
4. 영화 벡터 업데이트 실패 → 에러 로그, 사용자 취향은 업데이트됨

## 테스트

**테스트 파일**: `test_review_preference_pipeline.py`

**테스트 케이스**:
1. 긍정적 리뷰에서 업데이트 (5.0)
2. 부정적 리뷰에서 업데이트 (1.0)
3. 중립적 리뷰에서 업데이트 (3.0)
4. 취향 데이터 없이 업데이트 (에러 케이스)
5. 영화 벡터 없이 업데이트 (에러 케이스)

**테스트 실행**:
```bash
# 백엔드가 포트 8000에서 실행 중인지 확인
python test_review_preference_pipeline.py
```

## 향후 개선사항

### 즉시 (이미 구현됨)
- ✅ 리뷰 제출 시 취향 업데이트 트리거
- ✅ 사용자 취향 벡터 업데이트
- ✅ 영화 벡터 업데이트 (리뷰 텍스트 있을 때)
- ✅ 평점 기반 가중치
- ✅ 태그 관리 (boost/dislike)

### 단기 (구현 예정)
- [ ] 무거운 작업을 위한 백그라운드 태스크 처리
- [ ] 추천 목록 캐시 무효화
- [ ] 여러 리뷰 일괄 처리
- [ ] 리뷰 텍스트 감정 분석 개선

### 장기 (향후 고려사항)
- [ ] 협업 필터링 통합
- [ ] 취향 변화 기반 사용자 군집화
- [ ] 시간에 따른 취향 추적 (취향이 어떻게 변하는지)
- [ ] 다양한 학습률에 대한 A/B 테스트
- [ ] 취향 변화 감지 및 알림

## 설정

**조정 가능한 파라미터**:
- `learning_rate`: 취향이 얼마나 빨리 적응하는지 (0.01-0.5)
- `movie_learning_rate`: 영화 벡터가 얼마나 빨리 적응하는지 (0.01-0.2)
- `boost_tag_limit`: 최대 boost 태그 수 (기본값: 20)
- `dislike_tag_limit`: 최대 dislike 태그 수 (기본값: 15)
- `high_rating_threshold`: boost 태그 임계값 (기본값: 4.0)
- `low_rating_threshold`: dislike 태그 임계값 (기본값: 2.0)

## 모니터링

**추적할 주요 지표**:
- 취향 업데이트 성공률
- 평균 취향 벡터 변화 크기
- 영화 벡터 업데이트 빈도
- 리뷰-취향 업데이트 지연시간
- 유형별 에러율

## 의존성

**백엔드**:
- `repositories/user_preference.py`: 사용자 취향 데이터 접근
- `repositories/movie_vector.py`: 영화 벡터 데이터 접근
- `ml/model_sample/analysis/embedding.py`: LLM 기반 텍스트 분석
- `ml/data/emotion_tag.json`: 감정 분류 체계

**프론트엔드**:
- `api/userPreferences.ts`: API 클라이언트
- `pages/MovieDetailPage.tsx`: 리뷰 제출 UI
- `utils/preferenceSync.ts`: 취향 동기화 유틸리티

## 참고사항

- 취향 업데이트는 동기식(블로킹)으로 일관성 보장
- 취향 업데이트 실패해도 리뷰 제출은 막지 않음
- 영화 벡터는 안정성 유지를 위해 사용자 취향보다 천천히 변화
- 리뷰 텍스트 분석은 선택사항 - 평점만으로도 시스템 작동
- 모든 벡터 값은 [0, 1] 범위로 정규화됨
