# AI Service

Ultra-lightweight AI microservice for TaskHub - handles Chat, Content Generation, and KYC verification.

## Resource Usage

| Component | Disk | RAM | CPU |
|-----------|------|-----|-----|
| LLM (Gemma 3 270M Q4) | ~200MB | ~450MB | 1-2 cores (burst) |
| Face Detection + Recognition | ~15MB | ~120MB | <10% |
| OCR (Tesseract) | ~30MB | ~80MB | Moderate |
| FastAPI + LangChain | ~80MB | ~70MB | Minimal |
| **Total** | **~325MB** | **~720MB peak** | **2-4 cores** |

## Prerequisites

### 1. Python 3.12
```bash
python --version  # Should be 3.12.x
```

### 2. Tesseract OCR
**Windows:**
Download from: https://github.com/UB-Mannheim/tesseract/wiki

**Linux:**
```bash
apt-get install tesseract-ocr
```

### 3. Models (Auto-Download)

Models are **automatically downloaded** on first run. You can also download manually:

```bash
# Auto-download all models
python scripts/download_models.py

# Check model status
python scripts/download_models.py --check

# Skip LLM (for testing face/OCR only)
python scripts/download_models.py --skip-llm
```

**Models downloaded:**
| Model | Size | Purpose |
|-------|------|---------|
| gemma-3-270m-it-q4_k_m.gguf | ~200MB | Chat & content generation |
| ultra_light_face_slim.onnx | ~1MB | Face detection |
| mobilefacenet_int8.onnx | ~4MB | Face recognition |
| age_gender_mobilenet_int8.onnx | ~1.5MB | Age estimation |

Models are stored in `models/` directory (gitignored).

## Installation

```bash
# Create virtual environment
python -m venv .venv

# Activate
# Windows:
.\.venv\Scripts\Activate
# Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Configuration

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Key settings:
- `API_KEY`: Secret key for authentication
- `LLM_MODEL_PATH`: Path to GGUF model
- `LLM_THREADS`: CPU threads for LLM inference

## Running

```bash
# Development
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

# Production
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --workers 2
```

## API Endpoints

### Health
- `GET /api/v1/health` - Service health status

### Chat
- `POST /api/v1/chat` - Chat with AI

### Content Generation
- `POST /api/v1/generate/title` - Generate title from description
- `POST /api/v1/generate/description` - Generate description from title
- `POST /api/v1/generate/budget` - Suggest budget for task

### KYC
- `POST /api/v1/kyc/compare-faces` - Compare selfie with document photo
- `POST /api/v1/kyc/liveness` - Check if image is live capture
- `POST /api/v1/kyc/ocr` - Extract text from ID document
- `POST /api/v1/kyc/verify` - Complete KYC verification

## Backend Integration

Set environment variable in your backend:
```env
AI_SERVICE_URL=http://localhost:8001
AI_SERVICE_API_KEY=your-secret-key
```

## Architecture

```
ai-service/
├── app/
│   ├── main.py           # FastAPI app
│   ├── core/
│   │   └── config.py     # Settings
│   ├── api/
│   │   ├── routes.py     # API endpoints
│   │   └── schemas.py    # Pydantic models
│   ├── services/
│   │   ├── llm_service.py    # Gemma 3 via llama.cpp
│   │   ├── face_service.py   # Face detection/recognition
│   │   └── ocr_service.py    # Tesseract OCR
│   └── agents/
│       ├── router.py     # Intent routing
│       └── tools.py      # LangChain tools
├── models/               # Downloaded models (gitignored)
├── requirements.txt
└── .env
```
