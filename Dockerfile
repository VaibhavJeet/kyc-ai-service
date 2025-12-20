# KYC AI Microservice Dockerfile
# Multi-stage build for optimized image size

# ============= Builder Stage =============
FROM python:3.12-slim AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    git \
    libgl1 \
    libglx0 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ============= Production Stage =============
FROM python:3.12-slim

# Install runtime dependencies
# Required for insightface and paddleocr
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglx0 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create app directory
WORKDIR /app

# Create model cache directory with proper permissions
RUN mkdir -p /app/model_cache

# Copy application code
COPY app/ ./app/

# Create non-root user for security and set permissions
RUN groupadd -r kyc && useradd -r -g kyc kyc && \
    chown -R kyc:kyc /app

USER kyc

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    MODEL_CACHE_DIR=/app/model_cache \
    HOST=0.0.0.0 \
    PORT=8001 \
    WORKERS=2 \
    LD_PRELOAD=""

# Expose port
EXPOSE 8001

# Health check using curl (more reliable)
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD curl -f http://localhost:8001/api/v1/health || exit 1

# Run the application
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
