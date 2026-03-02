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
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "120", "web_app:create_app()"]
