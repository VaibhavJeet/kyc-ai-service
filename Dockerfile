# AI Service Dockerfile
# Ultra-lightweight: ~325MB disk, ~750MB RAM peak
# Multi-stage build for optimized image size

# ============= Builder Stage =============
FROM python:3.12-slim AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    git \
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
# - Tesseract for OCR
# - libgomp for ONNX Runtime
# - curl for health checks
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    libgomp1 libglib2.0-0 libsm6 libxext6 libxrender-dev libgl1 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean \
    && rm -rf /tmp/* /var/tmp/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create app directory
WORKDIR /app

# Create model directory (models will be downloaded at runtime)
RUN mkdir -p /app/models

# Copy application code
COPY app/ ./app/
COPY scripts/ ./scripts/

# Download InsightFace models at build time for faster startup
RUN python -c "import insightface; app = insightface.app.FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider']); app.prepare(ctx_id=0, det_size=(640, 640))" || true

# Models are downloaded automatically at runtime by app/main.py
# This reduces image size by ~325MB and allows models to be updated without rebuilding

# Create non-root user for security
RUN groupadd -r aiservice && useradd -r -g aiservice -m -d /home/aiservice aiservice && \
    chown -R aiservice:aiservice /app

USER aiservice

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HOST=0.0.0.0 \
    PORT=8001 \
    MODEL_CACHE_DIR=/app/models \
    HOME=/home/aiservice

# Expose port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8001/api/v1/health || exit 1

# Run the application
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
