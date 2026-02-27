# 테스트 및 문서

이 폴더에는 백엔드 API 테스트 파일과 관련 문서가 포함되어 있습니다.

## 테스트 파일

### API 테스트
- `test_backend_local.py` - 백엔드 로컬 환경 테스트
- `test_simple_api.py` - 간단한 API 테스트 (디버깅용)
- `test_user_preference_api.py` - 사용자 취향 API 테스트
- `test_review_api.py` - 리뷰 API 테스트

### 기능 테스트
- `test_review_preference_pipeline.py` - 리뷰 기반 취향 업데이트 파이프라인 테스트
- `test_user_preference.py` - 사용자 취향 기능 테스트
- `test_movie_vector.py` - 영화 벡터 기능 테스트
- `test_ml_integration.py` - ML 통합 테스트

## 문서

- `REVIEW_PREFERENCE_PIPELINE.md` - 리뷰 기반 취향 업데이트 파이프라인 상세 문서

## 테스트 실행 방법

### 사전 준비
1. 백엔드 서버가 실행 중이어야 합니다:
   ```bash
   uvicorn app:app --host 0.0.0.0 --port 8000
   ```

2. 가상환경이 활성화되어 있어야 합니다:
   ```bash
   # Windows
   venv\Scripts\activate
   
   # Linux/Mac
   source venv/bin/activate
   ```

### 개별 테스트 실행

```bash
# 사용자 취향 API 테스트
python tests/test_user_preference_api.py

# 리뷰 기반 취향 업데이트 파이프라인 테스트
python tests/test_review_preference_pipeline.py

# 간단한 API 테스트 (디버깅용)
python tests/test_simple_api.py
```

### 주의사항

- 테스트 실행 전에 데이터베이스가 정상적으로 연결되어 있는지 확인하세요
- 일부 테스트는 실제 사용자 데이터를 사용하므로 테스트 후 정리가 필요할 수 있습니다
- `test_review_preference_pipeline.py`는 기존 사용자 ID를 사용합니다 (파일 내 `EXISTING_USER_ID` 변수 확인)

## 테스트 결과 예시

성공적인 테스트 실행 시:
```
================================================================================
Review-Based Preference Update Pipeline Test Suite
================================================================================

=== Setup: Creating Test Data ===
User Preference Created: 201

=== Test: Update from Positive Review (5.0) ===
✓ PASS

...

Total: 7/7 tests passed
```

## 문제 해결

### 500 Internal Server Error
- 백엔드 터미널에서 에러 로그 확인
- 데이터베이스 연결 상태 확인
- 필요한 테이블이 모두 생성되어 있는지 확인

### Foreign Key Violation
- 테스트에 사용하는 user_id가 users 테이블에 존재하는지 확인
- `EXISTING_USER_ID` 변수를 실제 존재하는 사용자 ID로 변경

### 404 Not Found
- API 엔드포인트 경로가 올바른지 확인
- 백엔드 서버가 정상적으로 실행 중인지 확인
