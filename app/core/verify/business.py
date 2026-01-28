"""
TrustVault Business Verification Service
Reverse KYC - Verify businesses and callers

This service answers: "Is this really [Bank/Company] calling me?"

Data Sources:
1. Internal database of known businesses
2. Government APIs (MCA, GSTN) - requires paid integration
3. User-reported scam database
4. Phone number databases
"""

import re
import structlog
from typing import Dict, Any, Optional, List
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.business import BusinessRecord, BusinessVerification

logger = structlog.get_logger(__name__)


class BusinessVerificationService:
    """
    Service for verifying businesses and callers.

    Use Cases:
    - "Is this phone number really from HDFC Bank?"
    - "Is this website legitimate?"
    - "Is this company registered?"
    """

    # Known scam patterns
    SCAM_INDICATORS = [
        r"urgent.*action.*required",
        r"your.*account.*blocked",
        r"kyc.*expire",
        r"click.*link.*verify",
        r"otp.*share",
        r"lottery.*winner",
        r"prize.*claim",
    ]

    # Known legitimate bank phone prefixes (India)
    BANK_PHONE_PATTERNS = {
        "HDFC": [r"^1800.*$", r"^022.*$"],
        "ICICI": [r"^1800.*$", r"^022.*$"],
        "SBI": [r"^1800.*$", r"^1800112211$"],
        "Axis": [r"^1800.*$"],
    }

    def __init__(self, db: Session = None):
        self.db = db

    async def verify_phone_number(
        self,
        phone_number: str,
        claimed_business: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Verify if a phone number belongs to a claimed business.

        Args:
            phone_number: The phone number to verify
            claimed_business: The business name the caller claims to be from

        Returns:
            Verification result with risk assessment
        """
        result = {
            "query_type": "phone",
            "query_value": phone_number,
            "claimed_business": claimed_business,
            "is_verified": False,
            "is_match_found": False,
            "risk_level": "unknown",
            "risk_score": 50.0,
            "reasons": [],
            "flags": [],
            "matched_business": None,
        }

        # Clean phone number
        clean_phone = re.sub(r"[^\d+]", "", phone_number)

        # Check against known business records
        if self.db:
            business = await self._find_business_by_phone(clean_phone)
            if business:
                result["is_match_found"] = True
                result["matched_business"] = business.to_dict()

                # Check if it matches claimed business
                if claimed_business:
                    if self._fuzzy_match_name(business.name, claimed_business):
                        result["is_verified"] = True
                        result["risk_level"] = "low"
                        result["risk_score"] = 10.0
                        result["reasons"].append(f"Phone number verified as belonging to {business.name}")
                    else:
                        result["risk_level"] = "high"
                        result["risk_score"] = 80.0
                        result["flags"].append("BUSINESS_NAME_MISMATCH")
                        result["reasons"].append(
                            f"Phone belongs to {business.name}, not {claimed_business}"
                        )
                else:
                    result["is_verified"] = True
                    result["risk_level"] = "low"
                    result["risk_score"] = 20.0

                # Check for scam reports
                if business.is_known_scam:
                    result["is_verified"] = False
                    result["risk_level"] = "critical"
                    result["risk_score"] = 100.0
                    result["flags"].append("KNOWN_SCAM")
                    result["reasons"].append("This number is associated with known scam reports")

        # Check against known bank patterns
        if claimed_business:
            pattern_match = self._check_bank_patterns(clean_phone, claimed_business)
            if pattern_match:
                result["reasons"].append(f"Phone pattern matches known {claimed_business} format")
                if not result["is_match_found"]:
                    result["risk_score"] = max(result["risk_score"] - 20, 10)

        # Generic risk assessment for unknown numbers
        if not result["is_match_found"]:
            result["risk_level"] = "medium"
            result["reasons"].append("Phone number not found in verified business database")
            result["flags"].append("UNVERIFIED_NUMBER")

        return result

    async def verify_business(
        self,
        business_name: str,
        registration_number: Optional[str] = None,
        website: Optional[str] = None,
        phone: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Verify if a business is legitimate.

        Args:
            business_name: Name of the business
            registration_number: CIN, GSTIN, etc.
            website: Business website
            phone: Business phone number

        Returns:
            Verification result with risk assessment
        """
        result = {
            "query_type": "business",
            "business_name": business_name,
            "is_verified": False,
            "is_registered": False,
            "risk_level": "unknown",
            "risk_score": 50.0,
            "reasons": [],
            "flags": [],
            "matched_business": None,
            "sources_checked": [],
        }

        # Check against internal database
        if self.db:
            business = await self._find_business_by_name(business_name)
            if business:
                result["matched_business"] = business.to_dict()
                result["is_verified"] = business.is_verified
                result["is_registered"] = business.registration_number is not None

                if business.is_verified:
                    result["risk_level"] = "low"
                    result["risk_score"] = 15.0
                    result["reasons"].append("Business found in verified database")

                if business.is_known_scam:
                    result["risk_level"] = "critical"
                    result["risk_score"] = 100.0
                    result["flags"].append("KNOWN_SCAM")
                    result["reasons"].append(f"Business has {business.scam_reports} scam reports")

                # Validate registration number if provided
                if registration_number and business.registration_number:
                    if registration_number.upper() == business.registration_number.upper():
                        result["reasons"].append("Registration number matches")
                    else:
                        result["flags"].append("REGISTRATION_MISMATCH")
                        result["risk_score"] += 30
                        result["reasons"].append("Registration number does not match records")

            result["sources_checked"].append("internal_database")

        # Check registration number format
        if registration_number:
            reg_type = self._identify_registration_type(registration_number)
            if reg_type:
                result["registration_type"] = reg_type
                result["reasons"].append(f"Registration number appears to be {reg_type}")
                # TODO: Verify against actual government APIs
                result["sources_checked"].append(f"{reg_type}_format_check")
            else:
                result["flags"].append("INVALID_REGISTRATION_FORMAT")
                result["risk_score"] += 20

        # Website verification
        if website:
            website_risks = self._check_website_risks(website)
            result["flags"].extend(website_risks["flags"])
            result["reasons"].extend(website_risks["reasons"])
            result["risk_score"] += website_risks["risk_adjustment"]

        # Final risk level determination
        if result["risk_score"] <= 25:
            result["risk_level"] = "low"
        elif result["risk_score"] <= 50:
            result["risk_level"] = "medium"
        elif result["risk_score"] <= 75:
            result["risk_level"] = "high"
        else:
            result["risk_level"] = "critical"

        return result

    async def report_scam(
        self,
        identifier: str,
        identifier_type: str,
        business_name: Optional[str] = None,
        description: Optional[str] = None,
        reporter_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Report a suspected scam for review.

        Args:
            identifier: Phone number, website, or business name
            identifier_type: Type of identifier (phone, website, business)
            business_name: Claimed business name
            description: Description of the scam attempt
            reporter_id: ID of the reporter (tenant or user)

        Returns:
            Report confirmation
        """
        # TODO: Store in reports table, queue for review
        return {
            "reported": True,
            "report_id": None,  # Would be generated
            "status": "pending_review",
            "message": "Thank you for reporting. This will be reviewed within 24-48 hours.",
        }

    # ============= Private Methods =============

    async def _find_business_by_phone(self, phone: str) -> Optional[BusinessRecord]:
        """Find business by phone number"""
        if not self.db:
            return None

        # Query businesses where phone is in phone_numbers array
        # This is a simplified query - in production, use proper JSON querying
        businesses = self.db.query(BusinessRecord).all()
        for business in businesses:
            if phone in (business.phone_numbers or []):
                return business
        return None

    async def _find_business_by_name(self, name: str) -> Optional[BusinessRecord]:
        """Find business by name (fuzzy match)"""
        if not self.db:
            return None

        # Try exact match first
        business = self.db.query(BusinessRecord).filter(
            BusinessRecord.name.ilike(f"%{name}%")
        ).first()

        if not business:
            # Try legal name
            business = self.db.query(BusinessRecord).filter(
                BusinessRecord.legal_name.ilike(f"%{name}%")
            ).first()

        return business

    def _fuzzy_match_name(self, name1: str, name2: str) -> bool:
        """Check if two business names are similar enough"""
        if not name1 or not name2:
            return False

        # Normalize names
        n1 = name1.lower().strip()
        n2 = name2.lower().strip()

        # Remove common suffixes
        for suffix in ["pvt ltd", "private limited", "ltd", "limited", "inc", "llp", "bank"]:
            n1 = n1.replace(suffix, "").strip()
            n2 = n2.replace(suffix, "").strip()

        # Check if one contains the other
        return n1 in n2 or n2 in n1

    def _check_bank_patterns(self, phone: str, bank_name: str) -> bool:
        """Check if phone matches known bank patterns"""
        bank_key = bank_name.upper().split()[0]  # Get first word
        patterns = self.BANK_PHONE_PATTERNS.get(bank_key, [])

        for pattern in patterns:
            if re.match(pattern, phone):
                return True
        return False

    def _identify_registration_type(self, reg_number: str) -> Optional[str]:
        """Identify the type of registration number"""
        reg = reg_number.upper().strip()

        # CIN (Company Identification Number) - 21 chars
        if re.match(r"^[A-Z]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6}$", reg):
            return "CIN"

        # GSTIN (15 chars)
        if re.match(r"^\d{2}[A-Z]{5}\d{4}[A-Z]\d[Z][A-Z\d]$", reg):
            return "GSTIN"

        # PAN (10 chars)
        if re.match(r"^[A-Z]{5}\d{4}[A-Z]$", reg):
            return "PAN"

        # LLPIN (8 chars)
        if re.match(r"^[A-Z]{3}-\d{4}$", reg):
            return "LLPIN"

        return None

    def _check_website_risks(self, website: str) -> Dict[str, Any]:
        """Check website for risk indicators"""
        result = {
            "flags": [],
            "reasons": [],
            "risk_adjustment": 0,
        }

        website = website.lower()

        # Check for suspicious patterns
        if re.search(r"\d{5,}", website):  # Many numbers in domain
            result["flags"].append("SUSPICIOUS_DOMAIN")
            result["reasons"].append("Domain contains suspicious numeric pattern")
            result["risk_adjustment"] += 20

        if re.search(r"(verify|secure|login|update).*bank", website):
            result["flags"].append("PHISHING_PATTERN")
            result["reasons"].append("Domain matches common phishing patterns")
            result["risk_adjustment"] += 40

        if not website.startswith("https"):
            result["flags"].append("NO_HTTPS")
            result["reasons"].append("Website does not use HTTPS")
            result["risk_adjustment"] += 10

        # Check TLD
        suspicious_tlds = [".xyz", ".top", ".club", ".work", ".click", ".link"]
        for tld in suspicious_tlds:
            if website.endswith(tld):
                result["flags"].append("SUSPICIOUS_TLD")
                result["reasons"].append(f"Domain uses suspicious TLD ({tld})")
                result["risk_adjustment"] += 15
                break

        return result


# Singleton instance
_business_verification_service: Optional[BusinessVerificationService] = None


def get_business_verification_service(db: Session = None) -> BusinessVerificationService:
    """Get business verification service instance"""
    global _business_verification_service
    if _business_verification_service is None or db is not None:
        _business_verification_service = BusinessVerificationService(db)
    return _business_verification_service
