"""
TrustVault Python SDK - Client
"""

import httpx
from typing import Optional, Dict, Any
from .models import (
    FaceVerifyRequest, FaceVerifyResponse,
    KYCVerifyRequest, KYCVerifyResponse,
    TrustScoreRequest, TrustScoreResponse,
    BusinessVerifyRequest, BusinessVerifyResponse,
)


class TrustVaultError(Exception):
    """TrustVault API Error"""
    def __init__(self, message: str, status_code: int, details: Optional[Dict] = None):
        super().__init__(message)
        self.status_code = status_code
        self.details = details


class TrustVault:
    """
    TrustVault API Client
    
    Example:
        client = TrustVault(api_key="your-api-key")
        result = client.verify_kyc(
            selfie_base64="...",
            document_base64="...",
        )
    """
    
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.trustvault.io/v1",
        timeout: float = 30.0,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client = httpx.Client(
            base_url=self.base_url,
            headers={"X-API-Key": api_key},
            timeout=timeout,
        )
    
    def _request(self, method: str, path: str, json: Optional[Dict] = None) -> Dict:
        """Make HTTP request to API"""
        response = self._client.request(method, path, json=json)
        
        if response.status_code >= 400:
            try:
                error_data = response.json()
                message = error_data.get("detail", "Request failed")
            except:
                message = response.text or "Request failed"
            raise TrustVaultError(message, response.status_code)
        
        return response.json()
    
    def health(self) -> Dict[str, Any]:
        """Check API health status"""
        return self._request("GET", "/health")
    
    def verify_face(
        self,
        selfie_base64: str,
        document_base64: str,
    ) -> FaceVerifyResponse:
        """
        Compare two face images (selfie vs document)
        
        Args:
            selfie_base64: Base64 encoded selfie image
            document_base64: Base64 encoded document photo
            
        Returns:
            FaceVerifyResponse with match result and similarity score
        """
        data = self._request("POST", "/verify/face", json={
            "selfie_base64": selfie_base64,
            "document_base64": document_base64,
        })
        return FaceVerifyResponse(**data)
    
    def verify_liveness(self, image_base64: str) -> Dict[str, Any]:
        """
        Check if image is a live capture (anti-spoof)
        
        Args:
            image_base64: Base64 encoded face image
            
        Returns:
            Dict with is_live and score
        """
        return self._request("POST", "/verify/liveness", json={
            "image_base64": image_base64,
        })
    
    def verify_document(
        self,
        image_base64: str,
        document_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Extract information from ID document
        
        Args:
            image_base64: Base64 encoded document image
            document_type: Expected document type (optional)
            
        Returns:
            Dict with extracted document data
        """
        return self._request("POST", "/verify/document", json={
            "image_base64": image_base64,
            "document_type": document_type,
        })
    
    def verify_kyc(
        self,
        selfie_base64: str,
        document_base64: str,
        document_type: Optional[str] = None,
        expected_name: Optional[str] = None,
        expected_dob: Optional[str] = None,
    ) -> KYCVerifyResponse:
        """
        Complete KYC verification flow
        
        Args:
            selfie_base64: Base64 encoded selfie
            document_base64: Base64 encoded document
            document_type: Expected document type
            expected_name: Expected name for matching
            expected_dob: Expected DOB for matching
            
        Returns:
            KYCVerifyResponse with complete verification results
        """
        data = self._request("POST", "/verify/kyc", json={
            "selfie_base64": selfie_base64,
            "document_base64": document_base64,
            "document_type": document_type,
            "expected_name": expected_name,
            "expected_dob": expected_dob,
        })
        return KYCVerifyResponse(**data)
    
    def verify_business(
        self,
        business_name: str,
        phone_number: Optional[str] = None,
        registration_number: Optional[str] = None,
        website: Optional[str] = None,
    ) -> BusinessVerifyResponse:
        """
        Verify a business (Reverse KYC)
        
        Args:
            business_name: Name of business to verify
            phone_number: Phone number to check
            registration_number: CIN, GSTIN, etc.
            website: Business website
            
        Returns:
            BusinessVerifyResponse with verification result
        """
        data = self._request("POST", "/verify/business", json={
            "business_name": business_name,
            "phone_number": phone_number,
            "registration_number": registration_number,
            "website": website,
        })
        return BusinessVerifyResponse(**data)
    
    def calculate_trust_score(self, request: TrustScoreRequest) -> TrustScoreResponse:
        """
        Calculate trust score from verification signals
        
        Args:
            request: TrustScoreRequest with verification data
            
        Returns:
            TrustScoreResponse with score and decision
        """
        data = self._request("POST", "/trust/score", json=request.dict())
        return TrustScoreResponse(**data)
    
    def close(self):
        """Close the HTTP client"""
        self._client.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
