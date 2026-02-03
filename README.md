# Taste Simulation Engine

이 repo는 **AI 판단 엔진**과 **그 판단을 가능하게 만드는 데이터 파이프라인**을 함께 담는다.

**구성 축**
1. `ai/`: LLM / ML 로직 (두뇌)
2. `data/`: 영화 데이터 파이프라인 (재료)
3. `batch/`: 실행 단위 (오프라인 배치)

**빠른 시작**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**환경 변수 예시**
리포지토리 루트에 `.env` 파일을 생성하세요:
```dotenv
AWS_REGION=ap-northeast-2
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
BEDROCK_MAX_TOKENS=1024
BEDROCK_TEMPERATURE=0.2
```

**데이터 파이프라인 실행**
```powershell
python data/batch_runner.py
```
