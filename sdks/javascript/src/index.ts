/**
 * TrustVault JavaScript/TypeScript SDK
 * Official SDK for TrustVault API
 */

export interface TrustVaultConfig {
  apiKey: string;
  baseUrl?: string;
  timeout?: number;
}

export interface FaceVerifyRequest {
  selfieBase64: string;
  documentBase64: string;
}

export interface FaceVerifyResponse {
  match: boolean;
  similarity: number;
  threshold: number;
  confidence: string;
}

export interface KYCVerifyRequest {
  selfieBase64: string;
  documentBase64: string;
  documentType?: string;
}

export interface KYCVerifyResponse {
  faceMatch: boolean;
  faceSimilarity: number;
  isLive: boolean;
  livenessScore: number;
  trustScore: number;
  decision: string;
  confidence: string;
  overallPass: boolean;
  reasons: string[];
}

export interface TrustScoreResponse {
  score: number;
  decision: string;
  confidence: string;
  breakdown: Record<string, number>;
  reasons: string[];
  flags: string[];
}

class TrustVaultError extends Error {
  public statusCode: number;
  constructor(message: string, statusCode: number) {
    super(message);
    this.name = 'TrustVaultError';
    this.statusCode = statusCode;
  }
}

export default class TrustVault {
  private apiKey: string;
  private baseUrl: string;
  private timeout: number;

  constructor(config: TrustVaultConfig) {
    this.apiKey = config.apiKey;
    this.baseUrl = config.baseUrl || 'https://api.trustvault.io/v1';
    this.timeout = config.timeout || 30000;
  }

  private async request<T>(method: string, path: string, body?: any): Promise<T> {
    const response = await fetch(\`\${this.baseUrl}\${path}\`, {
      method,
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': this.apiKey,
      },
      body: body ? JSON.stringify(body) : undefined,
    });

    const data = await response.json();
    if (!response.ok) {
      throw new TrustVaultError(data.detail || 'Request failed', response.status);
    }
    return data as T;
  }

  async verifyFace(request: FaceVerifyRequest): Promise<FaceVerifyResponse> {
    return this.request('POST', '/verify/face', {
      selfie_base64: request.selfieBase64,
      document_base64: request.documentBase64,
    });
  }

  async verifyKYC(request: KYCVerifyRequest): Promise<KYCVerifyResponse> {
    return this.request('POST', '/verify/kyc', {
      selfie_base64: request.selfieBase64,
      document_base64: request.documentBase64,
      document_type: request.documentType,
    });
  }

  async getTrustScore(verificationId: string): Promise<TrustScoreResponse> {
    return this.request('GET', \`/trust/score/\${verificationId}\`);
  }

  async health(): Promise<{ status: string; version: string }> {
    return this.request('GET', '/health');
  }
}

export { TrustVault, TrustVaultError };
