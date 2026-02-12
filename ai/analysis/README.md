# 🧠 Analysis Modules (ML)

이 폴더는 영화 취향 분석 및 추천을 위한 ML 모듈들을 포함합니다.
기존 `movie_a_*.py` 파일들을 역할에 따라 직관적인 이름으로 정리했습니다.

## 📂 파일 구조 매핑

| 새로운 이름 | 기존 이름 | 설명 |
| :--- | :--- | :--- |
| **`sentiment.py`** | `movie_a_1.py` | 정서 기반 취향 모델링 (User Profile Builder) |
| **`embedding.py`** | `movie_a_2.py` | 영화 특성 추출, 벡터화 및 Bedrock 클라이언트 |
| **`similarity.py`** | `movie_a_3.py` | 취향 시뮬레이터 (코사인 유사도, 만족 확률 계산) |
| **`factor_analysis.py`** | `movie_a_4.py` | 추천 근거/기여 요소 분석 |
| **`description.py`** | `movie_a_5.py` | 자연어 추천 설명 생성 (LLM) |
| **`group_recommendation.py`** | `movie_a_6.py` | 그룹(다수 사용자) 만족도 통합 계산 |
| **`clustering.py`** | `movie_a_7.py` | 영화 취향 지도 (계층적 클러스터링) |
| **`visualization.py`** | `movie_a_8.py` | 사용자 프로필 워드클라우드 시각화 |
| **`cli.py`** | `movie_a_9.py` | 리뷰몽 CLI 시뮬레이터 실행 파일 |
| **`vector_db.py`** | `vector_utils.py` | 로컬 벡터 DB 유틸리티 (Numpy 기반) |
| **`preference.py`** | `movie_preference_builder.py` | 영화 선택 기반 취향 생성 도구 |

## 🚀 사용법 예시

### CLI 시뮬레이터 실행
```bash
python model_sample/analysis/cli.py
```

### 코드에서 import 사용 시
```python
from model_sample.analysis import sentiment, embedding

# ...
```
