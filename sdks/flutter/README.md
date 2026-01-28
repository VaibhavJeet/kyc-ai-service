# TrustVault Flutter SDK

Official Flutter SDK for TrustVault API.

## Installation

```yaml
# pubspec.yaml
dependencies:
  trustvault_sdk: ^1.0.0
```

## Quick Start

```dart
import 'package:trustvault_sdk/trustvault_sdk.dart';

final client = TrustVault(apiKey: 'tv_live_your_api_key');

// Full KYC verification
final result = await client.verify.kyc(
  selfieBase64: selfieImageBase64,
  documentBase64: documentImageBase64,
  documentType: 'aadhaar',
);

print(result.trustScore);    // 85.5
print(result.decision);      // VerificationDecision.autoVerified
print(result.faceMatch);     // true
```

## Features

### Face Verification
```dart
final result = await client.verify.face(
  selfieBase64: selfie,
  documentBase64: document,
);
```

### Liveness Check
```dart
final result = await client.verify.liveness(
  imageBase64: selfie,
);
```

### Document OCR
```dart
final result = await client.verify.document(
  imageBase64: documentImage,
  documentType: DocumentType.pan,
);
```

### Trust Score
```dart
final score = await client.trust.calculate(
  faceSimilarity: 0.92,
  livenessScore: 0.88,
  livenessPassed: true,
  documentConfidence: 0.95,
);
```

### Business Verification
```dart
final result = await client.verify.business(
  businessName: 'HDFC Bank',
  phoneNumber: '+911800202020',
);
```

## Camera Integration

```dart
import 'package:trustvault_sdk/widgets.dart';

// Use the built-in camera widget for selfie capture
TrustVaultCamera(
  mode: CameraMode.selfie,
  onCapture: (imageBase64) async {
    // Automatically does liveness check
    final result = await client.verify.liveness(imageBase64: imageBase64);
  },
);

// Document scanner
TrustVaultDocumentScanner(
  documentType: DocumentType.aadhaar,
  onCapture: (imageBase64) async {
    final result = await client.verify.document(imageBase64: imageBase64);
  },
);
```

## Error Handling

```dart
try {
  final result = await client.verify.kyc(...);
} on TrustVaultException catch (e) {
  print(e.code);     // ErrorCode.faceNotDetected
  print(e.message);  // "No face detected in selfie"
}
```
