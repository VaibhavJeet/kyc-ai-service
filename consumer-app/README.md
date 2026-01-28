# TrustVault Shield - Consumer Protection App

> Protect yourself from scams and fraud

## Features

### 1. Caller Verification
- Verify if a caller is really from your bank
- Real-time caller ID verification
- Automatic scam call blocking

### 2. Link/URL Checker
- Check if a link is safe before clicking
- Phishing detection
- Malware URL detection

### 3. Scam Reporting
- Report suspicious calls/messages
- Help protect the community
- View reported scams in your area

### 4. Family Protection
- Add family members to protect
- Get alerts when family receives suspicious calls
- Share verification results

## Screens

### Home Screen
- Protection status
- Quick actions
- Recent activity
- Safety tips

### Verify Caller Screen
- Enter phone number
- See caller identity
- Risk assessment
- Block/Report options

### Scam Check Screen
- Check phone numbers
- Check URLs/links
- Check businesses
- Scan QR codes

### Alerts Screen
- Scam alerts in your area
- Blocked calls history
- Family alerts

### Settings Screen
- Protection settings
- Family members
- Notification preferences
- Account settings

## Tech Stack

- Flutter 3.x
- Provider for state management
- TrustVault API integration
- Local notifications
- Call log access (with permission)

## Setup

```bash
# Install dependencies
flutter pub get

# Run the app
flutter run
```

## API Integration

The app connects to TrustVault API for:
- Phone number verification
- Business verification
- Scam database lookup
- Risk score calculation

## Privacy

- No call recording
- Minimal data collection
- All checks done via API
- User data encrypted
