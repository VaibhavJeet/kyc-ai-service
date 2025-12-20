# KYC AI Microservice

AI-powered identity verification service for TaskHub/Kamao Daily KYC processing.

## Features

- **Face Recognition**: ArcFace/InsightFace 512-dim embeddings for accurate face matching
- **Liveness Detection**: Multi-layer anti-spoofing (texture, frequency, color, moiré, reflection)
- **Document OCR**: PaddleOCR for extracting text from identity documents
- **Identity Scoring**: Unified scoring combining all verification signals
- **Age Estimation**: Built-in age estimation for DOB cross-validation

## Supported Documents

- Aadhaar Card
- PAN Card
- Passport (with MRZ parsing)
- Driving License
- Voter ID

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/health` | GET | Health check |
| `/api/v1/verify/face` | POST | Compare document and selfie faces |
| `/api/v1/verify/liveness` | POST | Passive liveness detection |
| `/api/v1/verify/document` | POST | Document OCR and type detection |
| `/api/v1/verify/complete` | POST | Complete KYC verification |
| `/api/v1/score/identity` | POST | Calculate identity score |

## Deployment with Coolify

### 1. Create New Service in Coolify

- Go to Coolify Dashboard
- Add New Resource > Docker
- Point to this repository

### 2. Environment Variables

Set these in Coolify:

```env
# Server
HOST=0.0.0.0
PORT=8001
WORKERS=2
DEBUG=false

# API Security (optional)
API_KEY=your-secure-api-key

# CORS
ALLOWED_ORIGINS=*

# Model Settings
MODEL_CACHE_DIR=/app/model_cache
USE_GPU=false

# Thresholds
FACE_MATCH_THRESHOLD=0.45
FACE_MATCH_HIGH_CONFIDENCE=0.55
LIVENESS_THRESHOLD=0.7
AGE_TOLERANCE=10

# Logging
LOG_LEVEL=INFO
```

### 3. Resource Limits

Recommended:
- CPU: 2 cores
- RAM: 2GB
- Disk: 5GB (for model cache)

### 4. Health Check

Coolify will use the health endpoint:
```
GET http://your-service:8001/api/v1/health
```

## Connect from Backend

In your NestJS backend, set the environment variable:

```env
KYC_AI_SERVICE_URL=http://kyc-ai-service:8001
KYC_AI_API_KEY=your-secure-api-key
```

If running on same VPS with Coolify, use the internal Docker network hostname.

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run server
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

## Docker Build

```bash
# Build
docker build -t kyc-ai-service .

# Run
docker run -p 8001:8001 -e API_KEY=your-key kyc-ai-service
```

## API Examples

### Complete Verification

```bash
curl -X POST http://localhost:8001/api/v1/verify/complete \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "document_image": "base64...",
    "selfie_image": "base64...",
    "expected_document_type": "aadhaar",
    "dob": "1990-01-15"
  }'
```

### Response

```json
{
  "score": 87.5,
  "decision": "auto_verified",
  "confidence": "high",
  "breakdown": {
    "face_match": 92.0,
    "liveness": 88.0,
    "document": 85.0,
    "age_consistency": 100.0,
    "uniqueness": 100.0,
    "risk": 95.0
  },
  "face_similarity": 0.92,
  "is_face_match": true,
  "is_live": true,
  "estimated_age": 34,
  "embedding_hash": "a1b2c3...",
  "fuzzy_hashes": ["L0_abc...", "L1_def...", "L2_ghi...", "L3_jkl..."]
}
```

## Privacy

- No images are stored
- Only privacy-preserving hashes used for deduplication
- All processing happens in-memory
- Complies with DPDP Act 2023 (India)
