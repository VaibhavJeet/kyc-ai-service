# TrustVault - Architecture & Product Design

## Product Name: **TrustVault**
> "Trust, Verified. Everywhere."

---

## Business Model

### What We Are
**API-First SaaS + PaaS** - A universal trust verification platform that can be:
1. **Consumed as API** (SaaS) - Businesses integrate via REST API
2. **Self-hosted** (PaaS) - Enterprises deploy on their infrastructure
3. **White-labeled** - Partners rebrand and resell

### Delivery Channels

| Channel | Description | Revenue Model |
|---------|-------------|---------------|
| **API SaaS** | REST API + Dashboard | Per-verification + Monthly subscription |
| **Mobile SDK** | iOS/Android SDKs | Included in API pricing |
| **Web SDK** | JavaScript widget | Included in API pricing |
| **Self-Hosted** | Docker/K8s deployment | License + Support contract |
| **White-Label** | Full rebrand | Setup fee + Revenue share |

---

## Product Offerings

### 1. Core Verification Services (B2B API)

| Service | Endpoint | Use Case |
|---------|----------|----------|
| **Face Verify** | `/v1/verify/face` | Compare selfie vs document |
| **Liveness Check** | `/v1/verify/liveness` | Anti-spoof detection |
| **Document OCR** | `/v1/verify/document` | Extract ID data |
| **Full KYC** | `/v1/verify/kyc` | Complete verification flow |
| **Trust Score** | `/v1/trust/score` | Unified trust rating |
| **Business Verify** | `/v1/verify/business` | Reverse KYC - verify companies |
| **Consent Proof** | `/v1/consent/record` | Video consent with liveness |

### 2. Consumer Protection (B2C App - Future)

| Feature | Description |
|---------|-------------|
| **Scam Shield** | Verify incoming callers/businesses |
| **Trust Passport** | Portable verified identity |
| **Alert System** | Family notifications on suspicious activity |

### 3. Enterprise Features

| Feature | Description |
|---------|-------------|
| **Multi-tenant** | Isolated data per organization |
| **Webhooks** | Real-time event notifications |
| **Audit Logs** | Compliance and forensics |
| **Custom Rules** | Configurable verification thresholds |
| **Analytics** | Verification metrics dashboard |

---

## Technical Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           TRUSTVAULT PLATFORM                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                        API GATEWAY                               │    │
│  │  • Rate Limiting  • API Key Auth  • Request Validation           │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                    │                                     │
│  ┌─────────────────────────────────┼─────────────────────────────────┐  │
│  │                                 │                                  │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐            │  │
│  │  │   VERIFY     │  │    TRUST     │  │   PROTECT    │            │  │
│  │  │   MODULE     │  │    MODULE    │  │   MODULE     │            │  │
│  │  │              │  │              │  │              │            │  │
│  │  │ • Face       │  │ • Score Calc │  │ • Scam Det   │            │  │
│  │  │ • Liveness   │  │ • Decision   │  │ • Alerts     │            │  │
│  │  │ • Document   │  │ • Confidence │  │ • Blocklist  │            │  │
│  │  │ • Business   │  │              │  │              │            │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘            │  │
│  │                                                                   │  │
│  │  ┌─────────────────────────────────────────────────────────────┐ │  │
│  │  │                    CORE SERVICES                             │ │  │
│  │  │  • InsightFace (Face AI)  • Tesseract (OCR)  • Gemma (LLM)  │ │  │
│  │  └─────────────────────────────────────────────────────────────┘ │  │
│  │                                                                   │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                    │                                     │
│  ┌─────────────────────────────────┼─────────────────────────────────┐  │
│  │                          DATA LAYER                               │  │
│  │  • PostgreSQL (Main DB)  • Redis (Cache)  • S3 (Media Storage)   │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Folder Structure (New)

```
trustvault/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI app entry
│   ├── config.py                  # Settings
│   │
│   ├── api/                       # API Layer
│   │   ├── __init__.py
│   │   ├── v1/                    # API Version 1
│   │   │   ├── __init__.py
│   │   │   ├── router.py          # Main router
│   │   │   ├── verify.py          # Verification endpoints
│   │   │   ├── trust.py           # Trust score endpoints
│   │   │   ├── protect.py         # Protection endpoints
│   │   │   ├── webhook.py         # Webhook management
│   │   │   └── health.py          # Health checks
│   │   └── schemas/               # Pydantic models
│   │       ├── __init__.py
│   │       ├── verify.py
│   │       ├── trust.py
│   │       ├── protect.py
│   │       └── common.py
│   │
│   ├── core/                      # Core Business Logic
│   │   ├── __init__.py
│   │   ├── verify/                # Verification Module
│   │   │   ├── __init__.py
│   │   │   ├── face.py            # Face verification
│   │   │   ├── liveness.py        # Liveness detection
│   │   │   ├── document.py        # Document OCR
│   │   │   ├── business.py        # Business verification (Reverse KYC)
│   │   │   └── consent.py         # Consent recording
│   │   │
│   │   ├── trust/                 # Trust Module
│   │   │   ├── __init__.py
│   │   │   ├── score.py           # Trust score calculation
│   │   │   ├── decision.py        # Decision engine
│   │   │   └── rules.py           # Custom rules engine
│   │   │
│   │   └── protect/               # Protection Module
│   │       ├── __init__.py
│   │       ├── scam_detect.py     # Scam detection
│   │       ├── alerts.py          # Alert system
│   │       └── blocklist.py       # Blocklist management
│   │
│   ├── services/                  # External Service Integrations
│   │   ├── __init__.py
│   │   ├── face_service.py        # InsightFace wrapper
│   │   ├── ocr_service.py         # Tesseract wrapper
│   │   ├── llm_service.py         # Gemma wrapper
│   │   ├── hash_service.py        # Embedding hashing
│   │   └── storage_service.py     # File storage
│   │
│   ├── middleware/                # Middleware
│   │   ├── __init__.py
│   │   ├── auth.py                # API key authentication
│   │   ├── rate_limit.py          # Rate limiting
│   │   ├── tenant.py              # Multi-tenant isolation
│   │   └── logging.py             # Request logging
│   │
│   ├── models/                    # Database Models
│   │   ├── __init__.py
│   │   ├── tenant.py              # Tenant/Organization
│   │   ├── api_key.py             # API Keys
│   │   ├── verification.py        # Verification records
│   │   ├── webhook.py             # Webhook configs
│   │   └── audit.py               # Audit logs
│   │
│   ├── db/                        # Database
│   │   ├── __init__.py
│   │   ├── session.py             # DB session
│   │   └── migrations/            # Alembic migrations
│   │
│   └── utils/                     # Utilities
│       ├── __init__.py
│       ├── crypto.py              # Encryption helpers
│       ├── validators.py          # Input validators
│       └── helpers.py             # General helpers
│
├── models/                        # ML Models (downloaded)
│   └── .gitkeep
│
├── scripts/                       # Utility scripts
│   ├── download_models.py
│   └── setup_db.py
│
├── tests/                         # Tests
│   ├── __init__.py
│   ├── test_verify.py
│   ├── test_trust.py
│   └── test_protect.py
│
├── docker/                        # Docker configs
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── docker-compose.prod.yml
│
├── docs/                          # Documentation
│   ├── api.md
│   ├── integration.md
│   └── deployment.md
│
├── .env.example
├── requirements.txt
├── README.md
└── ARCHITECTURE.md
```

---

## API Design (v1)

### Authentication
All API requests require `X-API-Key` header.

### Base URL
- Production: `https://api.trustvault.io/v1`
- Sandbox: `https://sandbox.trustvault.io/v1`

### Endpoints

#### Verification
```
POST /v1/verify/face          # Face comparison
POST /v1/verify/liveness      # Liveness check
POST /v1/verify/document      # Document OCR
POST /v1/verify/kyc           # Full KYC flow
POST /v1/verify/business      # Verify a business (Reverse KYC)
POST /v1/consent/record       # Record consent with video
```

#### Trust
```
POST /v1/trust/score          # Calculate trust score
GET  /v1/trust/score/{id}     # Get existing score
POST /v1/trust/decision       # Get verification decision
```

#### Management
```
GET  /v1/verifications        # List verifications
GET  /v1/verifications/{id}   # Get verification details
POST /v1/webhooks             # Create webhook
GET  /v1/webhooks             # List webhooks
DELETE /v1/webhooks/{id}      # Delete webhook
```

---

## Pricing Model (Draft)

### Starter (Free)
- 100 verifications/month
- Basic face + liveness
- Community support

### Growth ($99/month)
- 1,000 verifications/month
- Full KYC + Document OCR
- Webhooks
- Email support

### Business ($499/month)
- 10,000 verifications/month
- Business verification
- Custom rules
- Priority support

### Enterprise (Custom)
- Unlimited verifications
- Self-hosted option
- SLA guarantee
- Dedicated support

---

## Roadmap

### Phase 1 (MVP) - Current Sprint
- [x] Core face verification
- [x] Liveness detection
- [x] Document OCR
- [x] Trust score calculation
- [ ] API key management
- [ ] Multi-tenant isolation
- [ ] Webhook system

### Phase 2 (v1.0)
- [ ] Business verification (Reverse KYC)
- [ ] Consent recording
- [ ] Dashboard UI (separate repo)
- [ ] SDKs (Web, iOS, Android)

### Phase 3 (v2.0)
- [ ] Consumer app
- [ ] Scam detection
- [ ] AI-powered risk assessment
- [ ] Deepfake detection

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Python 3.12, FastAPI |
| Face AI | InsightFace (ArcFace) |
| OCR | Tesseract |
| LLM | Gemma 3 via llama.cpp |
| Database | PostgreSQL |
| Cache | Redis |
| Storage | S3-compatible |
| Auth | API Keys + JWT |
| Deployment | Docker, Kubernetes |

---

## Security Considerations

1. **Data Encryption** - All PII encrypted at rest (AES-256)
2. **API Security** - Rate limiting, IP allowlisting, key rotation
3. **Audit Logging** - All verification attempts logged
4. **Data Retention** - Configurable retention policies
5. **GDPR/CCPA** - Compliance features built-in
6. **No Image Storage** - Option to process without storing images

---

*Document Version: 1.0*
*Last Updated: January 2026*
