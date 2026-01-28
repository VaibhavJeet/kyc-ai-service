# TrustVault JavaScript SDK

Official JavaScript/TypeScript SDK for TrustVault API.

## Installation

```bash
npm install @trustvault/sdk
# or
yarn add @trustvault/sdk
```

## Quick Start

```typescript
import { TrustVault } from '@trustvault/sdk';

const client = new TrustVault({
  apiKey: 'tv_live_your_api_key',
  baseUrl: 'https://api.trustvault.io/v1', // optional
});

// Full KYC verification
const result = await client.verify.kyc({
  selfieBase64: 'base64_encoded_selfie',
  documentBase64: 'base64_encoded_document',
  documentType: 'aadhaar',
});

console.log(result.trustScore);    // 85.5
console.log(result.decision);      // "auto_verified"
console.log(result.faceMatch);     // true
```

## Features

### Face Verification
```typescript
const result = await client.verify.face({
  selfieBase64: selfie,
  documentBase64: document,
});
```

### Liveness Check
```typescript
const result = await client.verify.liveness({
  imageBase64: selfie,
});
```

### Document OCR
```typescript
const result = await client.verify.document({
  imageBase64: documentImage,
  documentType: 'pan', // optional
});
```

### Trust Score
```typescript
const score = await client.trust.calculate({
  faceSimilarity: 0.92,
  livenessScore: 0.88,
  livenessPassed: true,
  documentConfidence: 0.95,
});
```

### Business Verification
```typescript
const result = await client.verify.business({
  businessName: 'HDFC Bank',
  phoneNumber: '+911800202020',
});
```

## Browser Usage

```html
<script src="https://cdn.trustvault.io/sdk/v1/trustvault.min.js"></script>
<script>
  const client = new TrustVault({ apiKey: 'your_key' });
  // ...
</script>
```

## Error Handling

```typescript
try {
  const result = await client.verify.kyc({ ... });
} catch (error) {
  if (error instanceof TrustVaultError) {
    console.log(error.code);    // "FACE_NOT_DETECTED"
    console.log(error.message); // "No face detected in selfie"
  }
}
```

## TypeScript Support

Full TypeScript support with type definitions included.

```typescript
import { TrustVault, KYCResult, VerificationDecision } from '@trustvault/sdk';
```
