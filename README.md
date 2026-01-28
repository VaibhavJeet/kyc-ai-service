# TrustVault

> **Trust, Verified. Everywhere.**

Universal Trust Verification Platform - API-first SaaS for identity verification, business authentication, and fraud protection.

---

## What is TrustVault?

TrustVault is a comprehensive verification platform that answers the fundamental question of digital trust:

**"Can I trust this interaction right now?"**

Unlike traditional KYC solutions that only verify people, TrustVault verifies:
- **People** (Face, Liveness, Documents)
- **Businesses** (Reverse KYC - verify callers/companies)
- **Interactions** (Continuous trust scoring)

---

## Features

### Core Verification
- **Face Verification** - Compare selfie with ID document photo (InsightFace ArcFace 512-dim)
- **Liveness Detection** - Anti-spoofing to detect printed photos, screens, masks
- **Document OCR** - Extract data from Aadhaar, PAN, Passport, Driver's License
- **Full KYC Flow** - Complete verification in single API call

### Trust Score Engine
- **Unified Scoring** - Single 0-100 score from multiple verification signals
- **Decision Engine** - Auto-approve, manual review, or reject recommendations
- **Configurable Thresholds** - Customize per use-case

### Business Verification (Reverse KYC)
- **Caller Verification** - "Is this really my bank calling?"
- **Business Authentication** - Verify companies before transactions
- **Scam Protection** - Check against known fraud databases

### Platform Features
- **RESTful API** - Simple JSON API with comprehensive docs
- **Webhooks** - Real-time event notifications
- **Multi-tenant** - Isolated data per organization (coming soon)
- **Self-hosted Option** - Deploy on your infrastructure

---

## Resource Usage

| Component | Disk | RAM | CPU |
|-----------|------|-----|-----|
| Face AI (InsightFace) | ~300MB | ~200MB | 2-4 cores |
| LLM (Gemma 3 270M Q4) | ~200MB | ~450MB | 1-2 cores |
| OCR (Tesseract) | ~30MB | ~80MB | Moderate |
| FastAPI + Deps | ~80MB | ~70MB | Minimal |
| **Total** | **~325MB** | **~750MB peak** | **2-4 cores** |

---

## Quick Start

### Prerequisites
- Python 3.12+
- Tesseract OCR installed

**Windows:**
```bash
# Download from: https://github.com/UB-Mannheim/tesseract/wiki
```

**Linux:**
```bash
apt-get install tesseract-ocr
```

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/trustvault.git
cd trustvault

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# Edit .env and set your API key
# API_KEY=your-secure-api-key-here

# Run the server
python -m uvicorn app.main:app --reload --port 8000
```

Models are **automatically downloaded** on first run.

### First API Call

```bash
# Health check (no auth required)
curl http://localhost:8000/api/v1/health

# Face verification (auth required)
curl -X POST http://localhost:8000/api/v1/verify/face \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "selfie_base64": "base64-encoded-selfie-image",
    "document_base64": "base64-encoded-document-image"
  }'
```

---

## API Reference

### Base URL
- Local: `http://localhost:8000/api/v1`
- Production: `https://api.trustvault.io/v1`

### Authentication
All endpoints (except health) require `X-API-Key` header.

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/v1/health` | Health check |
| POST | `/v1/verify/face` | Compare two faces |
| POST | `/v1/verify/liveness` | Check if image is live |
| POST | `/v1/verify/document` | Extract document data |
| POST | `/v1/verify/kyc` | Complete KYC verification |
| POST | `/v1/verify/business` | Verify a business (Reverse KYC) |
| POST | `/v1/trust/score` | Calculate trust score |
| POST | `/v1/trust/decision` | Get verification decision |
| POST | `/v1/protect/scam-check` | Check for scam indicators |
| POST | `/v1/webhooks` | Create webhook |
| GET | `/v1/webhooks` | List webhooks |

### Example: Full KYC Verification

```python
import requests
import base64

# Read images
with open("selfie.jpg", "rb") as f:
    selfie_b64 = base64.b64encode(f.read()).decode()

with open("aadhaar.jpg", "rb") as f:
    document_b64 = base64.b64encode(f.read()).decode()

# Call API
response = requests.post(
    "http://localhost:8000/api/v1/verify/kyc",
    headers={"X-API-Key": "your-api-key"},
    json={
        "selfie_base64": selfie_b64,
        "document_base64": document_b64,
        "document_type": "aadhaar"
    }
)

result = response.json()
print(f"Trust Score: {result['trust_score']}")
print(f"Decision: {result['decision']}")
print(f"Face Match: {result['face_match']}")
print(f"Is Live: {result['is_live']}")
```

---

## Trust Score

The Trust Score combines multiple verification signals into a single confidence rating:

| Score Range | Decision | Meaning |
|-------------|----------|---------|
| 85-100 | `auto_verified` | High confidence - auto approve |
| 50-84 | `manual_review` | Medium confidence - needs review |
| 0-49 | `rejected` | Low confidence - reject |

### Score Components
- **Face Similarity** (30%) - How well selfie matches document
- **Liveness** (25%) - Anti-spoof detection confidence
- **Document Quality** (20%) - OCR confidence and type verification
- **Age Consistency** (10%) - Face age vs document DOB
- **Uniqueness** (15%) - No duplicate detection

---

## Configuration

Copy `.env.example` to `.env` and configure:

```bash
# Application
APP_NAME=TrustVault
DEBUG=true
ENVIRONMENT=development

# Server
HOST=0.0.0.0
PORT=8000

# Security
API_KEY=your-secure-api-key

# Verification Thresholds
FACE_MATCH_THRESHOLD=0.85
LIVENESS_THRESHOLD=0.6
TRUST_AUTO_APPROVE_THRESHOLD=0.85
TRUST_MANUAL_REVIEW_THRESHOLD=0.50
```

---

## Architecture

```
trustvault/
├── app/
│   ├── main.py                 # FastAPI application
│   ├── config.py               # Settings
│   ├── api/
│   │   └── v1/                 # API v1 endpoints
│   │       ├── verify.py       # Verification endpoints
│   │       ├── trust.py        # Trust score endpoints
│   │       ├── protect.py      # Protection endpoints
│   │       └── webhook.py      # Webhook management
│   ├── core/
│   │   ├── verify/             # Verification logic
│   │   ├── trust/              # Trust score engine
│   │   └── protect/            # Protection features
│   ├── services/
│   │   ├── face_service.py     # InsightFace wrapper
│   │   ├── ocr_service.py      # Tesseract wrapper
│   │   └── llm_service.py      # Gemma LLM
│   └── middleware/
│       └── auth.py             # API key authentication
├── models/                     # ML models (auto-downloaded)
├── docs/                       # Documentation
├── requirements.txt
└── .env
```

---

## Docker Deployment

```bash
# Build image
docker build -t trustvault:latest .

# Run container
docker run -d \
  -p 8000:8000 \
  -e API_KEY=your-api-key \
  -e DEBUG=false \
  trustvault:latest
```

---

## Use Cases

| Use Case | Description |
|----------|-------------|
| **Fintech KYC** | Verify customers for lending, crypto, neobanks |
| **HR Onboarding** | Remote employee identity verification |
| **P2P Marketplace** | Verify sellers on OLX, Facebook Marketplace |
| **Dating Apps** | Anti-catfish verification |
| **Elder Protection** | Verify callers to protect seniors from scams |
| **Gig Economy** | Portable verified identity for drivers, freelancers |

---

## Roadmap

### Phase 1 (Current)
- [x] Face verification with InsightFace
- [x] Liveness detection
- [x] Document OCR
- [x] Trust score engine
- [x] API key authentication
- [x] Webhook structure
- [ ] Database persistence
- [ ] Dashboard UI

### Phase 2
- [ ] Business verification APIs
- [ ] Consent recording with video
- [ ] Mobile SDKs (iOS, Android)
- [ ] Web SDK

### Phase 3
- [ ] Consumer protection app
- [ ] Scam detection AI
- [ ] Deepfake detection
- [ ] Continuous trust monitoring

---

## Contributing

Contributions welcome! Please read our contributing guidelines.

---

## License

MIT License

---

## Support

- Documentation: `/docs` endpoint
- Issues: GitHub Issues
- Email: support@trustvault.io

---

**TrustVault** - Trust, Verified. Everywhere.
