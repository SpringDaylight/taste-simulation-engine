# ML 모듈 - A-1~A-7 핵심 추천 시스템

이 폴더에는 정서·서사 기반 영화 추천 시스템의 핵심 ML 기능들이 포함되어 있습니다.

## 폴더 구조

```
ml/
├── data/                           # 데이터 파일
│   ├── emotion_tag.json           # 감정/서사 택소노미 (80개 태그)
│   └── movies_dataset_final.json  # 영화 데이터셋
│
└── model_sample/
    ├── analysis/                   # 핵심 분석 모듈
    │   ├── preference.py          # A-1: 사용자 취향 분석
    │   ├── embedding.py           # A-2: 영화 벡터화
    │   ├── similarity.py          # A-3: 만족 확률 계산
    │   ├── description.py         # A-4: 설명 생성
    │   ├── sentiment.py           # 감정 분석 유틸
    │   ├── group_recommendation.py # A-6: 그룹 추천
    │   ├── clustering.py          # A-7: 취향 지도
    │   ├── visualization.py       # 시각화 유틸
    │   ├── vector_db.py           # 벡터 DB 유틸
    │   ├── factor_analysis.py     # 요인 분석
    │   └── cli.py                 # CLI 도구
    │
    └── .env                        # AWS Bedrock 설정
```

## 핵심 기능 (A-1 ~ A-7)

### A-1: 사용자 취향 분석 (`analysis/preference.py`)
사용자가 입력한 텍스트(리뷰, 소감, 질의)를 분석하여 정서·서사 기반 취향 벡터 생성

**주요 기능:**
- 영화 선택 기반 세부 취향 추출
- 좋아하는/싫어하는 영화에서 태그 자동 추출
- 빈도 기반 필터링 (노이즈 제거)

### A-2: 영화 벡터화 (`analysis/embedding.py`)
영화 메타데이터를 분석하여 정서·서사 기반 특성 벡터 생성

**주요 기능:**
- LLM 기반 영화 분석 (AWS Bedrock Claude)
- Fallback: Deterministic 점수 생성
- 임베딩 벡터 생성 (AWS Bedrock Titan)
- 4개 차원 분석 (emotion, narrative, direction_mood, character_relationship)

### A-3: 만족 확률 계산 (`analysis/similarity.py`)
사용자 취향과 영화 특성 간 만족 확률 계산

**주요 기능:**
- 코사인 유사도 기반 계산
- Boost/Penalty 메커니즘
- 신뢰도 계산 (차원 간 일관성)
- 상세 breakdown 제공

### A-4: 설명 생성 (`analysis/description.py`)
만족 확률 결과를 자연어로 설명

**주요 기능:**
- LLM 기반 자연어 설명 생성
- Fallback: 템플릿 기반 설명
- 확률 구간별 다른 톤 (부정/중립/긍정)

### A-5: 감성 검색
자연어 쿼리를 감정 벡터로 변환 (Backend domain/a5_emotional_search.py에 구현)

### A-6: 그룹 추천 (`analysis/group_recommendation.py`)
여러 사용자의 취향을 종합하여 그룹 만족도 계산

**주요 기능:**
- Least Misery Strategy
- 멤버별 만족도 계산
- 그룹 통계 제공

### A-7: 취향 지도 (`analysis/clustering.py`)
영화 군집화 및 사용자 위치 시각화

**주요 기능:**
- UMAP 차원 축소
- K-Means 군집화
- 2D 좌표 생성

## Backend 통합

이 ML 모듈들은 Backend의 `domain/` 폴더에 통합되어 있습니다:

- `domain/a1_preference.py` - A-1 통합
- `domain/a2_movie_vector.py` - A-2 통합
- `domain/a3_prediction.py` - A-3 통합
- `domain/a4_explanation.py` - A-4 통합
- `domain/a5_emotional_search.py` - A-5 통합
- `domain/a6_group_simulation.py` - A-6 통합
- `domain/a7_taste_map.py` - A-7 통합

## 사용 방법

### 1. 직접 사용 (CLI)

```bash
# A-1: 사용자 취향 분석
cd ml/model_sample/analysis
python preference.py --liked 123,456 --disliked 789 --user-id user1

# A-2: 영화 벡터화
python embedding.py --movies ../data/movies_dataset_final.json --limit 10

# A-3: 만족 확률 계산
python similarity.py --user-text "감동적인 영화 좋아해요" --dislikes "무서워요"

# A-6: 그룹 추천
python group_recommendation.py --movie-id 123 --users "A:감동;B:웃김"
```

### 2. Backend API 사용 (권장)

```bash
# 서버 실행
uvicorn app:app --reload

# API 호출
curl -X POST http://localhost:8000/analyze/preference \
  -H "Content-Type: application/json" \
  -d '{"text": "감동적인 영화 좋아해요"}'
```

## 환경 설정

### AWS Bedrock 사용 시

`ml/model_sample/.env` 파일 생성:

```bash
AWS_REGION=ap-northeast-2
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret

BEDROCK_MODEL_ID=anthropic.claude-3-haiku-20240307-v1:0
BEDROCK_MAX_TOKENS=1024
BEDROCK_TEMPERATURE=0.2
```

### Fallback 모드

AWS 설정 없이도 deterministic 점수 생성으로 작동합니다.

## 데이터 파일

### emotion_tag.json
80개 태그로 구성된 택소노미:
- 감정 (emotion): 20개
- 서사 흐름 (story_flow): 20개
- 연출/분위기 (direction_mood): 20개
- 캐릭터/관계 (character_relationship): 20개

### movies_dataset_final.json
영화 데이터셋 (TMDB 기반):
- id, title, overview, genres, keywords
- directors, cast, release_date, runtime
- vote_average, vote_count

## 참고 문서

- [ML 기술보고서](../docs/ml%20기술보고서.md)
- [API Integration Guide](../API_INTEGRATION_GUIDE.md)
- [Integration Summary](../INTEGRATION_SUMMARY.md)

## 보관된 파일

리뷰몽, 칵테일 생성기 등 A-1~A-7과 직접 관련 없는 파일들은 `ml_archive/` 폴더에 보관되어 있습니다.

---

**최종 업데이트**: 2026-02-11  
**담당**: ML 팀
