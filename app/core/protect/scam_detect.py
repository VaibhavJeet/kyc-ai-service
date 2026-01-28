"""
TrustVault Scam Detection AI
ML-powered fraud and scam detection

Features:
- Phone number scam detection
- Website/URL analysis
- Message content analysis
- Pattern-based fraud detection
- ML model for scam classification
"""

import re
import structlog
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

logger = structlog.get_logger(__name__)


class RiskLevel(str, Enum):
    """Risk level classifications"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class ScamType(str, Enum):
    """Types of scams detected"""
    PHISHING = "phishing"
    IMPERSONATION = "impersonation"
    ADVANCE_FEE = "advance_fee"
    LOTTERY = "lottery"
    TECH_SUPPORT = "tech_support"
    ROMANCE = "romance"
    INVESTMENT = "investment"
    KYC_FRAUD = "kyc_fraud"
    OTP_FRAUD = "otp_fraud"
    UNKNOWN = "unknown"


@dataclass
class ScamIndicator:
    """Individual scam indicator"""
    type: str
    severity: float  # 0-1
    description: str
    evidence: str


class ScamDetectionService:
    """
    AI-powered scam detection service.

    Uses multiple detection methods:
    1. Pattern matching (regex)
    2. Keyword analysis
    3. URL/domain analysis
    4. Phone number database lookup
    5. ML classification (future)
    """

    # Scam keyword patterns
    SCAM_PATTERNS = {
        "urgent_action": [
            r"urgent\s+action\s+required",
            r"immediate\s+attention",
            r"act\s+now",
            r"limited\s+time",
            r"expires?\s+today",
        ],
        "kyc_fraud": [
            r"kyc\s+(update|verify|expire|pending)",
            r"account\s+(block|suspend|freeze)",
            r"verify\s+your\s+(identity|account|details)",
            r"complete\s+kyc\s+immediately",
        ],
        "otp_fraud": [
            r"share\s+(your\s+)?otp",
            r"send\s+(me\s+)?otp",
            r"otp\s+for\s+verification",
            r"give\s+(me\s+)?the\s+code",
        ],
        "lottery_fraud": [
            r"you\s+(have\s+)?won",
            r"lottery\s+winner",
            r"prize\s+claim",
            r"lucky\s+draw",
            r"congratulations.*winner",
        ],
        "phishing": [
            r"click\s+(here|this)\s+link",
            r"verify\s+by\s+clicking",
            r"login\s+to\s+confirm",
            r"update\s+your\s+password",
        ],
        "impersonation": [
            r"this\s+is\s+(from\s+)?.*bank",
            r"calling\s+from\s+.*department",
            r"government\s+official",
            r"police\s+department",
            r"income\s+tax\s+department",
        ],
        "money_request": [
            r"transfer\s+money",
            r"send\s+payment",
            r"processing\s+fee",
            r"advance\s+payment",
            r"registration\s+fee",
        ],
    }

    # Suspicious URL patterns
    SUSPICIOUS_URL_PATTERNS = [
        r".*-login.*",
        r".*-verify.*",
        r".*-secure.*",
        r".*-update.*",
        r".*bit\.ly.*",
        r".*tinyurl.*",
        r".*\d{5,}.*",  # Many numbers
    ]

    # Known legitimate domains (whitelist)
    LEGITIMATE_DOMAINS = [
        "hdfcbank.com",
        "icicibank.com",
        "sbi.co.in",
        "axisbank.com",
        "kotak.com",
        "paytm.com",
        "phonepe.com",
        "gpay.app",
        "amazon.in",
        "flipkart.com",
    ]

    # Known scam domains (blacklist) - would be from database in production
    KNOWN_SCAM_DOMAINS: List[str] = []

    def __init__(self):
        # Compile regex patterns for efficiency
        self._compiled_patterns: Dict[str, List[re.Pattern]] = {}
        for category, patterns in self.SCAM_PATTERNS.items():
            self._compiled_patterns[category] = [
                re.compile(p, re.IGNORECASE) for p in patterns
            ]

    async def analyze_message(
        self,
        message: str,
        sender: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Analyze a message for scam indicators.

        Args:
            message: Message content to analyze
            sender: Sender identifier (phone, email, etc.)
            metadata: Additional context

        Returns:
            Analysis result with risk assessment
        """
        indicators: List[ScamIndicator] = []
        detected_types: List[str] = []

        # Pattern matching
        for category, patterns in self._compiled_patterns.items():
            for pattern in patterns:
                match = pattern.search(message)
                if match:
                    indicators.append(ScamIndicator(
                        type=category,
                        severity=0.7,
                        description=f"Detected {category.replace('_', ' ')} pattern",
                        evidence=match.group()
                    ))
                    detected_types.append(category)
                    break  # One match per category

        # URL analysis
        urls = self._extract_urls(message)
        for url in urls:
            url_risk = self._analyze_url(url)
            if url_risk["is_suspicious"]:
                indicators.append(ScamIndicator(
                    type="suspicious_url",
                    severity=url_risk["severity"],
                    description=url_risk["reason"],
                    evidence=url
                ))

        # Calculate overall risk
        risk_score = self._calculate_risk_score(indicators)
        risk_level = self._get_risk_level(risk_score)

        # Determine scam type
        scam_type = self._determine_scam_type(detected_types)

        return {
            "is_suspicious": risk_score > 30,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "scam_type": scam_type,
            "indicators": [
                {
                    "type": i.type,
                    "severity": i.severity,
                    "description": i.description,
                    "evidence": i.evidence,
                }
                for i in indicators
            ],
            "recommendation": self._get_recommendation(risk_level, scam_type),
            "analyzed_at": datetime.utcnow().isoformat(),
        }

    async def analyze_phone(
        self,
        phone_number: str,
        claimed_identity: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Analyze a phone number for scam indicators.

        Args:
            phone_number: Phone number to check
            claimed_identity: Who the caller claims to be

        Returns:
            Analysis result
        """
        clean_phone = re.sub(r"[^\d+]", "", phone_number)
        indicators: List[ScamIndicator] = []

        # Check phone format
        if not self._is_valid_indian_phone(clean_phone):
            indicators.append(ScamIndicator(
                type="invalid_format",
                severity=0.3,
                description="Invalid phone number format",
                evidence=phone_number
            ))

        # Check for VoIP indicators
        if self._is_voip_number(clean_phone):
            indicators.append(ScamIndicator(
                type="voip_number",
                severity=0.4,
                description="VoIP/virtual number detected",
                evidence=clean_phone
            ))

        # Check against known scam numbers (would be from database)
        # For demo, using placeholder
        is_reported_scam = False  # Would check database
        if is_reported_scam:
            indicators.append(ScamIndicator(
                type="reported_scam",
                severity=1.0,
                description="Number reported as scam by multiple users",
                evidence=clean_phone
            ))

        # Check claimed identity vs known numbers
        if claimed_identity:
            identity_check = self._verify_claimed_identity(clean_phone, claimed_identity)
            if not identity_check["matches"]:
                indicators.append(ScamIndicator(
                    type="identity_mismatch",
                    severity=0.8,
                    description=identity_check["reason"],
                    evidence=f"Claimed: {claimed_identity}"
                ))

        risk_score = self._calculate_risk_score(indicators)
        risk_level = self._get_risk_level(risk_score)

        return {
            "phone_number": clean_phone,
            "is_suspicious": risk_score > 30,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "indicators": [
                {"type": i.type, "description": i.description}
                for i in indicators
            ],
            "claimed_identity": claimed_identity,
            "recommendation": self._get_recommendation(risk_level, "phone"),
        }

    async def analyze_url(self, url: str) -> Dict[str, Any]:
        """
        Analyze a URL for phishing/scam indicators.

        Args:
            url: URL to analyze

        Returns:
            Analysis result
        """
        result = self._analyze_url(url)
        risk_level = self._get_risk_level(result["severity"] * 100)

        return {
            "url": url,
            "is_suspicious": result["is_suspicious"],
            "risk_score": result["severity"] * 100,
            "risk_level": risk_level,
            "reason": result["reason"],
            "domain": result.get("domain"),
            "recommendation": self._get_recommendation(risk_level, "phishing"),
        }

    # ============= Private Methods =============

    def _extract_urls(self, text: str) -> List[str]:
        """Extract URLs from text"""
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        return re.findall(url_pattern, text)

    def _analyze_url(self, url: str) -> Dict[str, Any]:
        """Analyze a single URL"""
        url_lower = url.lower()

        # Extract domain
        domain_match = re.search(r'https?://([^/]+)', url_lower)
        domain = domain_match.group(1) if domain_match else ""

        # Check whitelist
        for legit_domain in self.LEGITIMATE_DOMAINS:
            if legit_domain in domain:
                return {
                    "is_suspicious": False,
                    "severity": 0,
                    "reason": "Known legitimate domain",
                    "domain": domain,
                }

        # Check blacklist
        for scam_domain in self.KNOWN_SCAM_DOMAINS:
            if scam_domain in domain:
                return {
                    "is_suspicious": True,
                    "severity": 1.0,
                    "reason": "Known scam domain",
                    "domain": domain,
                }

        # Check suspicious patterns
        for pattern in self.SUSPICIOUS_URL_PATTERNS:
            if re.search(pattern, url_lower):
                return {
                    "is_suspicious": True,
                    "severity": 0.7,
                    "reason": "URL matches suspicious pattern",
                    "domain": domain,
                }

        # Check for lookalike domains
        lookalike = self._check_lookalike_domain(domain)
        if lookalike["is_lookalike"]:
            return {
                "is_suspicious": True,
                "severity": 0.9,
                "reason": f"Possible lookalike of {lookalike['similar_to']}",
                "domain": domain,
            }

        return {
            "is_suspicious": False,
            "severity": 0.2,  # Unknown domain has some risk
            "reason": "Unknown domain",
            "domain": domain,
        }

    def _check_lookalike_domain(self, domain: str) -> Dict[str, Any]:
        """Check if domain is lookalike of legitimate domain"""
        lookalike_patterns = [
            (r"hdf[c1l]bank", "hdfcbank.com"),
            (r"ic[i1l]c[i1l]bank", "icicibank.com"),
            (r"sb[i1l]", "sbi.co.in"),
            (r"ax[i1l]sbank", "axisbank.com"),
            (r"payt[mn]", "paytm.com"),
        ]

        for pattern, original in lookalike_patterns:
            if re.search(pattern, domain) and original not in domain:
                return {"is_lookalike": True, "similar_to": original}

        return {"is_lookalike": False}

    def _is_valid_indian_phone(self, phone: str) -> bool:
        """Check if phone is valid Indian format"""
        clean = phone.replace("+91", "").replace(" ", "")
        return len(clean) == 10 and clean.isdigit() and clean[0] in "6789"

    def _is_voip_number(self, phone: str) -> bool:
        """Check if phone appears to be VoIP"""
        # VoIP detection is complex - this is simplified
        # In production, use a phone number intelligence API
        return False

    def _verify_claimed_identity(
        self,
        phone: str,
        claimed_identity: str
    ) -> Dict[str, Any]:
        """Verify if phone matches claimed identity"""
        # Would check against database of known business numbers
        return {"matches": True, "reason": "Could not verify"}

    def _calculate_risk_score(self, indicators: List[ScamIndicator]) -> float:
        """Calculate overall risk score (0-100)"""
        if not indicators:
            return 0

        # Weighted average with max boost
        total_severity = sum(i.severity for i in indicators)
        count = len(indicators)

        # More indicators = higher risk
        base_score = (total_severity / count) * 100
        indicator_boost = min(count * 10, 30)  # Up to 30% boost

        return min(base_score + indicator_boost, 100)

    def _get_risk_level(self, score: float) -> str:
        """Convert risk score to level"""
        if score >= 80:
            return RiskLevel.CRITICAL.value
        elif score >= 60:
            return RiskLevel.HIGH.value
        elif score >= 30:
            return RiskLevel.MEDIUM.value
        elif score > 0:
            return RiskLevel.LOW.value
        else:
            return RiskLevel.UNKNOWN.value

    def _determine_scam_type(self, detected_types: List[str]) -> str:
        """Determine most likely scam type"""
        type_mapping = {
            "kyc_fraud": ScamType.KYC_FRAUD.value,
            "otp_fraud": ScamType.OTP_FRAUD.value,
            "lottery_fraud": ScamType.LOTTERY.value,
            "phishing": ScamType.PHISHING.value,
            "impersonation": ScamType.IMPERSONATION.value,
            "money_request": ScamType.ADVANCE_FEE.value,
        }

        for detected in detected_types:
            if detected in type_mapping:
                return type_mapping[detected]

        return ScamType.UNKNOWN.value

    def _get_recommendation(self, risk_level: str, scam_type: str) -> str:
        """Get user-friendly recommendation"""
        recommendations = {
            RiskLevel.CRITICAL.value: "DO NOT engage. This is very likely a scam. Block and report immediately.",
            RiskLevel.HIGH.value: "High risk of scam. Do not share any personal information or OTP. Verify independently.",
            RiskLevel.MEDIUM.value: "Exercise caution. Verify the sender through official channels before responding.",
            RiskLevel.LOW.value: "Low risk, but always verify unexpected requests through official channels.",
        }
        return recommendations.get(risk_level, "Unable to assess risk. Proceed with caution.")


# Singleton
_scam_detection_service: Optional[ScamDetectionService] = None


def get_scam_detection_service() -> ScamDetectionService:
    """Get scam detection service instance"""
    global _scam_detection_service
    if _scam_detection_service is None:
        _scam_detection_service = ScamDetectionService()
    return _scam_detection_service
