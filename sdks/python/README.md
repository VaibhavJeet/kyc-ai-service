# TrustVault Python SDK

Official Python SDK for TrustVault API.

## Installation

```bash
pip install trustvault
```

## Quick Start

```python
from trustvault import TrustVault

client = TrustVault(api_key="tv_live_your_api_key")

# Full KYC verification
result = client.verify.kyc(
    selfie_base64="base64_encoded_selfie",
    document_base64="base64_encoded_document",
    document_type="aadhaar"
)

print(result.trust_score)    # 85.5
print(result.decision)       # "auto_verified"
print(result.face_match)     # True
```

## Features

### Face Verification
```python
result = client.verify.face(
    selfie_base64=selfie,
    document_base64=document
)
```

### Liveness Check
```python
result = client.verify.liveness(image_base64=selfie)
```

### Document OCR
```python
result = client.verify.document(
    image_base64=document_image,
    document_type="pan"  # optional
)
```

### Trust Score
```python
score = client.trust.calculate(
    face_similarity=0.92,
    liveness_score=0.88,
    liveness_passed=True,
    document_confidence=0.95
)
```

### Business Verification
```python
result = client.verify.business(
    business_name="HDFC Bank",
    phone_number="+911800202020"
)
```

## Async Support

```python
from trustvault import AsyncTrustVault

client = AsyncTrustVault(api_key="your_key")

result = await client.verify.kyc(...)
```

## Error Handling

```python
from trustvault import TrustVaultError

try:
    result = client.verify.kyc(...)
except TrustVaultError as e:
    print(e.code)     # "FACE_NOT_DETECTED"
    print(e.message)  # "No face detected in selfie"
```
