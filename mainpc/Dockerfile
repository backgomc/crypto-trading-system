FROM tensorflow/tensorflow:2.15.0-gpu
WORKDIR /app

# 시스템 필수 패키지 설치
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# requirements 복사
COPY requirements.txt .

# CuPy 포함 모든 패키지 설치
RUN pip install --no-cache-dir --ignore-installed -r requirements.txt

# 앱 소스 복사
COPY . .

# 포트 오픈
EXPOSE 5000

# 실행 명령
CMD ["python", "ai_server.py"]
