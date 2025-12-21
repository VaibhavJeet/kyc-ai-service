"""
Hash Service - Privacy-Preserving Face and Document Hashing
Generates SHA256 and fuzzy (LSH) hashes for duplicate detection
without storing actual biometric data.

Features:
1. Embedding Hash - SHA256 of quantized face embedding
2. Fuzzy Hashes (LSH) - Locality-sensitive hashes at multiple granularities
3. Document Hash - SHA256 of document number/ID

NOTE: This is SERVER-SIDE hash generation. The Flutter app already
generates these hashes on-device. This service is for:
- Validating client-provided hashes
- Generating hashes when images are processed server-side
- Duplicate detection queries
"""

import hashlib
import numpy as np
import structlog
from typing import List, Optional, Tuple

logger = structlog.get_logger(__name__)


class HashService:
    """Privacy-preserving hash generation for duplicate detection"""

    # Salt for additional security (should be in env in production)
    SALT = "kamaodaily_salt_v1"

    def generate_embedding_hash(self, embedding: np.ndarray) -> str:
        """
        Generate SHA256 hash from face embedding.
        Quantizes embedding to reduce minor variations while preserving identity.

        Args:
            embedding: L2-normalized face embedding (128 or 512 dimensions)

        Returns:
            SHA256 hex string
        """
        # Quantize embedding to 256 levels (-1 to 1 -> 0 to 255)
        quantized = ((embedding + 1) * 127.5).astype(np.uint8)

        # Convert to bytes and hash
        embedding_bytes = quantized.tobytes()
        hash_obj = hashlib.sha256(embedding_bytes + self.SALT.encode())
        return hash_obj.hexdigest()

    def generate_fuzzy_hashes(
        self,
        embedding: np.ndarray,
        num_levels: int = 4
    ) -> List[str]:
        """
        Generate fuzzy hashes using locality-sensitive hashing (LSH).
        Creates multiple hashes at different quantization levels for robust matching.

        L0 = fine-grained (64 levels) - catches exact matches
        L1 = medium (32 levels) - catches minor variations
        L2 = coarse (16 levels) - catches moderate changes (glasses, lighting)
        L3 = very coarse (8 levels) - catches significant changes (aging, beard)

        Args:
            embedding: L2-normalized face embedding
            num_levels: Number of hash levels to generate (default 4)

        Returns:
            List of fuzzy hashes like ["L0_abc123...", "L1_def456...", ...]
        """
        hashes = []

        for level in range(num_levels):
            # Different quantization levels: 64, 32, 16, 8
            num_bins = 64 >> level

            # Quantize to fewer levels
            quantized = ((embedding + 1) * (num_bins / 2)).astype(np.int32)
            quantized = np.clip(quantized, 0, num_bins - 1)

            # Pack into bytes
            quantized_bytes = quantized.astype(np.uint8).tobytes()

            # Hash with level prefix
            hash_obj = hashlib.sha256(quantized_bytes + f"_L{level}_{self.SALT}".encode())
            short_hash = hash_obj.hexdigest()[:16]  # Use first 16 chars
            hashes.append(f"L{level}_{short_hash}")

        return hashes

    def generate_document_hash(
        self,
        document_number: Optional[str] = None,
        masked_id: Optional[str] = None,
        document_type: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> str:
        """
        Generate SHA256 hash for document deduplication.

        Args:
            document_number: Full document number (e.g., PAN, Passport)
            masked_id: Masked Aadhaar (xxxx-xxxx-1234)
            document_type: Type of document
            user_id: User ID (fallback for uniqueness)

        Returns:
            SHA256 hex string
        """
        if document_number:
            data = document_number
        elif masked_id:
            data = masked_id
        elif user_id and document_type:
            # Fallback: hash user + type + timestamp
            import time
            data = f"{user_id}_{document_type}_{int(time.time())}"
        else:
            raise ValueError("No document identifier provided")

        hash_obj = hashlib.sha256((data + self.SALT).encode())
        return hash_obj.hexdigest()

    def compare_fuzzy_hashes(
        self,
        hashes1: List[str],
        hashes2: List[str]
    ) -> Tuple[int, float]:
        """
        Compare two sets of fuzzy hashes to determine if they match.

        Returns:
            Tuple of (matching_levels, confidence)
            - matching_levels: Number of hash levels that match (0-4)
            - confidence: 0.0-1.0 likelihood of same person
        """
        # Extract levels and hashes
        hash_dict1 = {h.split('_')[0]: h for h in hashes1}
        hash_dict2 = {h.split('_')[0]: h for h in hashes2}

        matches = 0
        total = 0

        for level in ['L0', 'L1', 'L2', 'L3']:
            if level in hash_dict1 and level in hash_dict2:
                total += 1
                if hash_dict1[level] == hash_dict2[level]:
                    matches += 1

        if total == 0:
            return 0, 0.0

        # Weight coarser levels more (they're more tolerant)
        # L0 match = 0.15, L1 = 0.20, L2 = 0.30, L3 = 0.35
        weights = {'L0': 0.15, 'L1': 0.20, 'L2': 0.30, 'L3': 0.35}
        weighted_score = 0.0

        for level in ['L0', 'L1', 'L2', 'L3']:
            if level in hash_dict1 and level in hash_dict2:
                if hash_dict1[level] == hash_dict2[level]:
                    weighted_score += weights.get(level, 0.25)

        return matches, weighted_score

    def validate_hash_format(self, hash_str: str) -> bool:
        """Validate that a hash string is in expected format"""
        if hash_str.startswith('L') and '_' in hash_str:
            # Fuzzy hash format: L0_abc123...
            parts = hash_str.split('_')
            return len(parts) == 2 and len(parts[1]) == 16
        else:
            # SHA256 format: 64 hex chars
            return len(hash_str) == 64 and all(c in '0123456789abcdef' for c in hash_str.lower())


# Singleton
_hash_service: Optional[HashService] = None


def get_hash_service() -> HashService:
    """Get or create hash service instance"""
    global _hash_service
    if _hash_service is None:
        _hash_service = HashService()
    return _hash_service
