# ML Archive - 보관된 파일들

이 폴더에는 리뷰몽(게이미피케이션), 칵테일 생성기 등 A-1~A-7 핵심 추천 시스템과 직접 관련 없는 ML 실험 코드들이 보관되어 있습니다.

## 보관된 항목

### 1. 리뷰몽 (MovieMong) - 게이미피케이션 시스템
- `moviemong/` - 캐릭터 육성, 밥주기, 리뷰 분석 시스템
- `app_moviemong.py` - 리뷰몽 Flask 앱
- `database.py`, `models.py` - 리뷰몽 전용 DB 모델
- `moviemong.db` - SQLite 데이터베이스
- `리뷰몽` - 실행 파일
- `task.md`, `walkthrough.md` - 리뷰몽 개발 문서

**주요 기능:**
- 캐릭터 성장 시스템 (Lv.1 알 → 성체)
- 밥주기 룰렛 (팝콘, 핫도그, 콤보, 오징어, 치킨)
- 리뷰 분석 및 맛 스탯 (Sweet, Spicy, Onion, Salty, Cheese, Dark, Mint, Original)

### 2. 칵테일 생성기 (Emotion Cocktail)
- `cocktail/` - 감정 기반 칵테일 추천 시스템
- `app_cocktail.py` - 칵테일 Flask 앱
- `templates/cocktail.html` - 칵테일 UI

**주요 기능:**
- 감정 분석 기반 칵테일 추천
- 이미지 렌더링
- 감정 검증

### 3. UI 리소스
- `static/` - 리뷰몽 이미지 (1차, 2차, 3차, 유아기, 최종, 배경)
- `templates/` - HTML 템플릿

### 4. 데이터 파일
- `daily_questions.json` - 일일 질문 데이터
- `movies_translate.json` - 영화 번역 데이터
- `translation_cache.json` - 번역 캐시

## 현재 Git에 포함된 ML 파일 (A-1~A-7 관련)

### ml/data/
- `emotion_tag.json` - 감정/서사 택소노미 (80개 태그)
- `movies_dataset_final.json` - 영화 데이터셋

### ml/model_sample/analysis/
- `preference.py` - A-1: 사용자 취향 분석
- `embedding.py` - A-2: 영화 벡터화
- `similarity.py` - A-3: 만족 확률 계산
- `description.py` - A-4: 설명 생성
- `sentiment.py` - 감정 분석 유틸
- `group_recommendation.py` - A-6: 그룹 추천
- `clustering.py` - A-7: 취향 지도
- `visualization.py` - 시각화 유틸
- `vector_db.py` - 벡터 DB 유틸
- `factor_analysis.py` - 요인 분석
- `cli.py` - CLI 도구
- `README.md` - 분석 모듈 문서

### ml/model_sample/
- `.env` - 환경 변수 (AWS Bedrock 설정)

## 복원 방법

필요시 다음 명령으로 파일을 복원할 수 있습니다:

```bash
# 리뷰몽 복원
move ml_archive\moviemong ml\model_sample\
move ml_archive\app_moviemong.py ml\
move ml_archive\database.py ml\model_sample\
move ml_archive\models.py ml\model_sample\
move ml_archive\moviemong.db ml\data\

# 칵테일 복원
move ml_archive\cocktail ml\model_sample\
move ml_archive\app_cocktail.py ml\

# UI 리소스 복원
move ml_archive\static ml\
move ml_archive\templates ml\
```

## 참고

이 파일들은 삭제되지 않고 보관되어 있으므로, 향후 필요시 언제든지 복원하여 사용할 수 있습니다.

---

**보관 일자**: 2026-02-11  
**보관 이유**: Git 커밋 정리 - A-1~A-7 핵심 추천 시스템만 포함
