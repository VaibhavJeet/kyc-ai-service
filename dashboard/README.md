# TrustVault Dashboard

Admin dashboard for TrustVault - manage verifications, view analytics, configure settings.

## Tech Stack (Recommended)

- **Framework**: Next.js 14+ (App Router)
- **UI**: Tailwind CSS + shadcn/ui
- **State**: Zustand or React Query
- **Charts**: Recharts or Tremor
- **Auth**: NextAuth.js

## Features

### 1. Dashboard Overview
- Total verifications (today/week/month)
- Success/failure rates
- Trust score distribution
- Recent activity feed

### 2. Verifications
- List all verifications with filters
- View verification details
- Manual review queue
- Export to CSV

### 3. Analytics
- Verification trends over time
- Geographic distribution
- Document type breakdown
- Risk level distribution

### 4. API Keys
- Create/revoke API keys
- View usage per key
- Set rate limits
- IP whitelisting

### 5. Webhooks
- Configure webhook endpoints
- View delivery logs
- Test webhooks
- Retry failed deliveries

### 6. Settings
- Organization profile
- Team members (future)
- Billing (future)
- Custom thresholds

## Quick Start

```bash
# Create Next.js app
npx create-next-app@latest trustvault-dashboard --typescript --tailwind --app

cd trustvault-dashboard

# Install dependencies
npm install @tanstack/react-query axios recharts lucide-react
npx shadcn-ui@latest init

# Add components
npx shadcn-ui@latest add button card table badge input

# Run dev server
npm run dev
```

## Project Structure

```
dashboard/
├── app/
│   ├── layout.tsx
│   ├── page.tsx              # Dashboard overview
│   ├── verifications/
│   │   ├── page.tsx          # List verifications
│   │   └── [id]/page.tsx     # Verification details
│   ├── analytics/
│   │   └── page.tsx
│   ├── api-keys/
│   │   └── page.tsx
│   ├── webhooks/
│   │   └── page.tsx
│   └── settings/
│       └── page.tsx
├── components/
│   ├── ui/                   # shadcn components
│   ├── charts/
│   ├── tables/
│   └── layout/
├── lib/
│   ├── api.ts               # API client
│   └── utils.ts
└── types/
    └── index.ts
```

## API Integration

```typescript
// lib/api.ts
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export const api = {
  // Verifications
  getVerifications: (params) => fetch(`${API_BASE}/verifications?${new URLSearchParams(params)}`),
  getVerification: (id) => fetch(`${API_BASE}/verifications/${id}`),

  // API Keys
  getApiKeys: () => fetch(`${API_BASE}/api-keys`),
  createApiKey: (data) => fetch(`${API_BASE}/api-keys`, { method: 'POST', body: JSON.stringify(data) }),

  // Webhooks
  getWebhooks: () => fetch(`${API_BASE}/webhooks`),
  createWebhook: (data) => fetch(`${API_BASE}/webhooks`, { method: 'POST', body: JSON.stringify(data) }),

  // Analytics
  getAnalytics: (period) => fetch(`${API_BASE}/analytics?period=${period}`),
};
```

## Deployment

### Vercel (Recommended)
```bash
vercel
```

### Docker
```dockerfile
FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build
CMD ["npm", "start"]
```

## Environment Variables

```bash
NEXT_PUBLIC_API_URL=https://api.trustvault.io
NEXTAUTH_SECRET=your-secret
NEXTAUTH_URL=https://dashboard.trustvault.io
```
