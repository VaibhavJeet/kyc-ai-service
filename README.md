# TrustVault

> **Trust, Verified. Everywhere.**

A Universal Trust Verification Platform that goes beyond traditional KYC to answer the fundamental question of digital trust: **"Can I trust this interaction right now?"**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/Python-3.12+-green.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-teal.svg)](https://fastapi.tiangolo.com)

---

## Overview

TrustVault is an API-first verification platform that verifies:

| What | How |
|------|-----|
| **People** | Face comparison, liveness detection, document OCR |
| **Businesses** | Reverse KYC - verify callers and companies |
| **Interactions** | Continuous trust scoring, fraud detection |

Unlike traditional KYC (one-time, reactive, identity-only), TrustVault provides **continuous, proactive, context-aware trust**.

---

## Features

### Core Verification
- **Face Verification** - Compare selfie with ID document photo using InsightFace ArcFace (512-dim embeddings)
- **Liveness Detection** - Anti-spoofing to detect printed photos, screens, and masks
- **Document OCR** - Extract data from Aadhaar, PAN, Passport, Driver's License using Tesseract

### Trust Intelligence
- **Trust Score (0-100)** - Unified scoring from multiple verification signals
- **Decision Engine** - Auto-approve, manual review, or reject recommendations
- **Configurable Thresholds** - Customize per use-case

### Business Verification (Reverse KYC)
- **Caller Verification** - "Is this really my bank calling?"
- **Business Authentication** - Verify companies before transactions
- **Scam Protection** - Check against known fraud patterns

### Platform
- **RESTful API** - Simple JSON API with OpenAPI docs
- **Webhooks** - Real-time event notifications
- **Multi-tenant** - Isolated data per organization
- **Self-hosted Option** - Deploy on your infrastructure

---

## Resource Requirements

| Component | Disk | RAM | CPU |
|-----------|------|-----|-----|
| Face AI (InsightFace) | ~300MB | ~200MB | 2-4 cores |
| LLM (Gemma 3 270M Q4) | ~200MB | ~450MB | 1-2 cores |
| OCR (Tesseract) | ~30MB | ~80MB | Moderate |
| FastAPI + Dependencies | ~80MB | ~70MB | Minimal |
| **Total** | **~325MB** | **~750MB peak** | **2-4 cores** |

Lightweight enough to run on a $5/month VPS.

---

## Quick Start

### Prerequisites

- Python 3.12+
- Tesseract OCR

**Windows:**
```bash
# Download installer from: https://github.com/UB-Mannheim/tesseract/wiki
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get install tesseract-ocr
```

**macOS:**
```bash
brew install tesseract
```

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/trustvault.git
cd trustvault

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and set: API_KEY=your-secure-api-key-here

# Start the server
python -m uvicorn app.main:app --reload --port 8000
```

Models download automatically on first run.

### Verify Installation

```bash
# Health check (no auth required)
curl http://localhost:8000/api/v1/health

# Expected response:
# {"status": "healthy", "version": "1.0.0"}
```

---

## API Reference

### Base URL

| Environment | URL |
|-------------|-----|
| Local | `http://localhost:8000/api/v1` |
| Production | `https://api.trustvault.io/v1` |

### Authentication

All endpoints (except `/health`) require the `X-API-Key` header:

```bash
curl -H "X-API-Key: your-api-key" http://localhost:8000/api/v1/...
```

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/v1/health` | Health check |
| `POST` | `/v1/verify/face` | Compare two faces |
| `POST` | `/v1/verify/liveness` | Anti-spoof detection |
| `POST` | `/v1/verify/document` | Extract document data |
| `POST` | `/v1/verify/kyc` | Complete KYC verification |
| `POST` | `/v1/verify/business` | Verify a business (Reverse KYC) |
| `POST` | `/v1/trust/score` | Calculate trust score |
| `POST` | `/v1/trust/decision` | Get verification decision |
| `POST` | `/v1/protect/scam-check` | Check for scam indicators |
| `POST` | `/v1/webhooks` | Create webhook |
| `GET` | `/v1/webhooks` | List webhooks |

### Example: Face Verification

```bash
curl -X POST http://localhost:8000/api/v1/verify/face \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "selfie_base64": "<base64-encoded-selfie>",
    "document_base64": "<base64-encoded-document>"
  }'
```

**Response:**
```json
{
  "match": true,
  "similarity": 0.92,
  "confidence": "high"
}
```

### Example: Full KYC Flow

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

### Score Components

| Component | Weight | Description |
|-----------|--------|-------------|
| Face Similarity | 30% | Selfie matches document photo |
| Liveness | 25% | Anti-spoof detection confidence |
| Document Quality | 20% | OCR confidence and type verification |
| Age Consistency | 10% | Face age vs document DOB |
| Uniqueness | 15% | No duplicate detection |

### Decision Thresholds

| Score | Decision | Meaning |
|-------|----------|---------|
| 85-100 | `auto_verified` | High confidence - auto approve |
| 50-84 | `manual_review` | Medium confidence - needs review |
| 0-49 | `rejected` | Low confidence - reject |

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

## Project Structure

```
trustvault/
├── app/
│   ├── main.py              # FastAPI application
│   ├── config.py            # Settings
│   ├── api/
│   │   └── v1/              # API v1 endpoints
│   │       ├── verify.py    # Verification endpoints
│   │       ├── trust.py     # Trust score endpoints
│   │       ├── protect.py   # Protection endpoints
│   │       └── webhook.py   # Webhook management
│   ├── core/
│   │   ├── verify/          # Verification logic
│   │   ├── trust/           # Trust score engine
│   │   └── protect/         # Protection features
│   ├── models/              # Database models
│   ├── services/
│   │   ├── face_service.py  # InsightFace wrapper
│   │   ├── ocr_service.py   # Tesseract wrapper
│   │   └── llm_service.py   # Gemma LLM
│   └── middleware/
│       └── auth.py          # API key authentication
├── dashboard/               # Next.js dashboard (scaffold)
├── sdks/
│   ├── javascript/          # NPM package
│   ├── python/              # PyPI package
│   └── flutter/             # Pub.dev package
├── models/                  # ML models (auto-downloaded)
├── requirements.txt
├── .env.example
└── README.md
```

---

## SDKs

### JavaScript/TypeScript

```bash
npm install @trustvault/sdk
```

```javascript
import { TrustVault } from '@trustvault/sdk';

const client = new TrustVault({ apiKey: 'your-api-key' });

const result = await client.verify.kyc({
  selfieBase64: selfieData,
  documentBase64: documentData,
  documentType: 'aadhaar'
});

console.log(`Trust Score: ${result.trustScore}`);
```

### Python

```bash
pip install trustvault
```

```python
from trustvault import TrustVault

client = TrustVault(api_key="your-api-key")

result = client.verify.kyc(
    selfie_base64=selfie_data,
    document_base64=document_data,
    document_type="aadhaar"
)

print(f"Trust Score: {result.trust_score}")
```

### Flutter/Dart

```yaml
dependencies:
  trustvault: ^1.0.0
```

```dart
import 'package:trustvault/trustvault.dart';

final client = TrustVault(apiKey: 'your-api-key');

final result = await client.verify.kyc(
  selfieBase64: selfieData,
  documentBase64: documentData,
  documentType: 'aadhaar',
);

print('Trust Score: ${result.trustScore}');
```

---

## Docker Deployment

### Build and Run

```bash
# Build image
docker build -t trustvault:latest .

# Run container
docker run -d \
  -p 8000:8000 \
  -e API_KEY=your-api-key \
  -e DEBUG=false \
  --name trustvault \
  trustvault:latest
```

### Docker Compose

```yaml
version: '3.8'
services:
  trustvault:
    build: .
    ports:
      - "8000:8000"
    environment:
      - API_KEY=${API_KEY}
      - DEBUG=false
    volumes:
      - ./models:/app/models
    restart: unless-stopped
```

---

## Use Cases

| Industry | Use Case |
|----------|----------|
| **Fintech** | KYC for lending apps, crypto exchanges, neobanks |
| **HR** | Remote employee identity verification, background checks |
| **Marketplaces** | Verify sellers on P2P platforms (OLX, Facebook Marketplace) |
| **Dating** | Anti-catfish verification with "Verified Human" badges |
| **Elder Care** | Protect seniors from phone scams, verify callers |
| **Gig Economy** | Portable verified identity for drivers, freelancers |
| **Real Estate** | Tenant KYC for landlords and property managers |
| **Age-Restricted** | Verification for alcohol, gaming, adult content platforms |
| **Childcare** | Verify tutors, nannies, caregivers before hiring |
| **Home Services** | Real-time verification when service workers enter homes |

---

## Roadmap

### Phase 1: Foundation (Current)
- [x] Face verification with InsightFace
- [x] Liveness detection
- [x] Document OCR
- [x] Trust score engine
- [x] API key authentication
- [x] Webhook structure
- [x] SDKs (JavaScript, Python, Flutter)
- [ ] Database persistence
- [ ] Dashboard UI

### Phase 2: Platform
- [ ] Business verification APIs (Reverse KYC)
- [ ] Consent recording with video
- [ ] Mobile SDKs (iOS, Android native)
- [ ] Multi-tenant isolation

### Phase 3: Protection
- [ ] Consumer protection app
- [ ] Scam detection AI
- [ ] Deepfake detection
- [ ] Continuous trust monitoring

### Phase 4: Scale
- [ ] Platform integrations
- [ ] AI agent verification
- [ ] Web3 identity integration

---

## API Documentation

Interactive API documentation is available at:

- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`

---

## Contributing

Contributions are welcome! Please read our [Contributing Guidelines](CONTRIBUTING.md) before submitting PRs.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Support

- **Documentation:** [/docs endpoint](http://localhost:8000/docs)
- **Issues:** [GitHub Issues](https://github.com/yourusername/trustvault/issues)
- **Email:** support@trustvault.io

---

<p align="center">
  <strong>TrustVault</strong> - Trust, Verified. Everywhere.
</p>
