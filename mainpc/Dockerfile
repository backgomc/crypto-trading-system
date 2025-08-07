# 파일 경로: mainpc/Dockerfile
FROM tensorflow/tensorflow:2.15.0-gpu
WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# ⭐ Flask API 서버 포트 노출
EXPOSE 5000

# ⭐ Flask 서버 실행으로 변경
CMD ["python", "ai_server.py"]