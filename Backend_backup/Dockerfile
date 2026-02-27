FROM python:3.11-slim

WORKDIR /app

# 한글 폰트 (NanumGothic) 설치 - 워드클라우드 한글 렌더링용
RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-nanum \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
