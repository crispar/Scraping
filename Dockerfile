FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        libxml2-dev \
        libxslt1-dev && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir flask gunicorn

# Copy source code
COPY src/ src/
COPY setup.py .
COPY README.md .
COPY web_app.py .
COPY templates/ templates/
COPY static/ static/

# Install the package (non-editable for production)
RUN pip install --no-cache-dir .

EXPOSE 5000

# Run with gunicorn
# 비동기 추출(job_id + 폴링) 저장소가 프로세스 로컬이므로 워커는 반드시 1개.
# 워커가 여러 개면 POST를 받은 워커와 폴링을 받은 워커가 달라 job을 못 찾는다.
# 대신 --threads로 동시 요청(폴링 여러 건 + 백그라운드 추출)을 처리한다.
# timeout 600s: 백그라운드 추출 스레드가 도는 동안 워커가 죽지 않도록 여유.
# nginx proxy_read_timeout(600s)과 맞춰둠 (폴링은 짧지만 여유값 유지).
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--threads", "8", "--worker-class", "gthread", "--timeout", "600", "web_app:create_app()"]
