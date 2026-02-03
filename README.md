# Taste Simulation Engine

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
