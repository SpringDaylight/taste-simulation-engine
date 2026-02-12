# 데이터 파이프라인

이 폴더는 영화 데이터를 수집하고 가공해 **서비스가 바로 쓸 수 있는 자산**으로 만드는 영역이다.  
AI 로직(`ai/`)과 절대 섞지 않고, 같은 repo 안에서 별도 축으로 관리한다.

**폴더 구조**
- `raw/`: 원천 데이터 수집
- `preprocess/`: 정제/정규화
- `llm_enrich/`: LLM 기반 영화 해석 (A-2)
- `embedding/`: 임베딩 생성
- `index/`: 벡터 인덱싱
- `batch_runner.py`: 전체 파이프라인 실행

**실행 흐름**
```text
raw -> preprocess -> llm_enrich -> embedding -> index
```

**로컬 실행**
```powershell
python data/batch_runner.py
```
