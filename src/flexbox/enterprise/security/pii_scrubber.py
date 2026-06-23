"""PII Scrubber - removes personally identifiable information from prompts."""

import re
from typing import Optional
from dataclasses import dataclass, field
from enum import Enum


class PIICategory(Enum):
    """Categories of PII."""
    EMAIL = "email"
    PHONE = "phone"
    SSN = "ssn"
    CREDIT_CARD = "credit_card"
    NAME = "name"
    ADDRESS = "address"
    IP_ADDRESS = "ip_address"
    DATE_OF_BIRTH = "date_of_birth"
    PASSPORT = "passport"
    DRIVER_LICENSE = "driver_license"


@dataclass
class PIIDetection:
    """Detected PII instance."""
    category: PIICategory
    value: str
    start: int
    end: int
    confidence: float


@dataclass
class ScrubResult:
    """Result of PII scrubbing."""
    original_length: int
    scrubbed_length: int
    pii_found: int
    pii_removed: int
    detections: list[PIIDetection] = field(default_factory=list)
    categories_found: dict[str, int] = field(default_factory=dict)


class PIIScrubber:
    """
    Scrubs personally identifiable information from text.
    
    Features:
    - Multi-category PII detection
    - Configurable confidence thresholds
    - Custom pattern support
    - Replacement strategies (mask, redact, hash)
    """

    # Built-in patterns
    PATTERNS = {
        PIICategory.EMAIL: [
            (r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", 0.9),
        ],
        PIICategory.PHONE: [
            (r"(?i)(\+?1?[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", 0.8),
            (r"(?i)\+\d{1,3}[-.\s]?\d{4,14}", 0.85),
        ],
        PIICategory.SSN: [
            (r"\d{3}-\d{2}-\d{4}", 0.95),
            (r"(?i)social\s+security\s+(?:number|no\.?)\s*:?\s*\d{3}-\d{2}-\d{4}", 0.95),
        ],
        PIICategory.CREDIT_CARD: [
            (r"\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}", 0.9),
            (r"(?i)(?:credit|debit|card)\s+(?:number|no\.?)\s*:?\s*\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}", 0.95),
        ],
        PIICategory.IP_ADDRESS: [
            (r"\b(?:\d{1,3}\.){3}\d{1,3}\b", 0.85),
        ],
        PIICategory.DATE_OF_BIRTH: [
            (r"(?i)(?:date\s+of\s+birth|dob|born)\s*:?\s*\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}", 0.8),
            (r"(?i)\d{1,2}[/\-]\d{1,2}[/\-]\d{4}", 0.6),
        ],
        PIICategory.PASSPORT: [
            (r"(?i)passport\s+(?:number|no\.?)\s*:?\s*[A-Z0-9]{6,12}", 0.85),
        ],
        PIICategory.DRIVER_LICENSE: [
            (r"(?i)driver'?s?\s+license\s+(?:number|no\.?)\s*:?\s*[A-Z0-9]{6,20}", 0.8),
        ],
    }

    def __init__(
        self,
        confidence_threshold: float = 0.7,
        replacement_strategy: str = "mask",
        custom_patterns: Optional[dict[PIICategory, list[tuple[str, float]]]] = None,
    ):
        self.confidence_threshold = confidence_threshold
        self.replacement_strategy = replacement_strategy
        self._patterns = self.PATTERNS.copy()
        
        if custom_patterns:
            for category, patterns in custom_patterns.items():
                if category in self._patterns:
                    self._patterns[category].extend(patterns)
                else:
                    self._patterns[category] = patterns

    def scrub(self, text: str) -> tuple[str, ScrubResult]:
        """
        Scrub PII from text.
        
        Args:
            text: Input text
            
        Returns:
            Tuple of (scrubbed_text, result)
        """
        detections = self.detect(text)
        
        original_length = len(text)
        scrubbed = text
        
        # Apply replacements in reverse order to preserve positions
        for detection in sorted(detections, key=lambda d: d.start, reverse=True):
            replacement = self._get_replacement(detection)
            scrubbed = scrubbed[:detection.start] + replacement + scrubbed[detection.end:]
        
        categories_found = {}
        for d in detections:
            cat = d.category.value
            categories_found[cat] = categories_found.get(cat, 0) + 1
        
        result = ScrubResult(
            original_length=original_length,
            scrubbed_length=len(scrubbed),
            pii_found=len(detections),
            pii_removed=len(detections),
            detections=detections,
            categories_found=categories_found,
        )
        
        return scrubbed, result

    def detect(self, text: str) -> list[PIIDetection]:
        """
        Detect PII in text without removing.
        
        Returns:
            List of PIIDetection instances
        """
        detections = []
        
        for category, patterns in self._patterns.items():
            for pattern, confidence in patterns:
                compiled = re.compile(pattern)
                
                for match in compiled.finditer(text):
                    if confidence >= self.confidence_threshold:
                        detections.append(PIIDetection(
                            category=category,
                            value=match.group(),
                            start=match.start(),
                            end=match.end(),
                            confidence=confidence,
                        ))
        
        # Sort by position
        detections.sort(key=lambda d: d.start)
        
        # Remove overlapping detections (keep higher confidence)
        filtered = []
        last_end = 0
        
        for detection in detections:
            if detection.start >= last_end:
                filtered.append(detection)
                last_end = detection.end
        
        return filtered

    def _get_replacement(self, detection: PIIDetection) -> str:
        """Get replacement text for a PII detection."""
        if self.replacement_strategy == "mask":
            return self._mask_value(detection)
        elif self.replacement_strategy == "redact":
            return f"[REDACTED_{detection.category.value.upper()}]"
        elif self.replacement_strategy == "hash":
            import hashlib
            hashed = hashlib.sha256(detection.value.encode()).hexdigest()[:8]
            return f"[HASH:{hashed}]"
        else:
            return "[REDACTED]"

    def _mask_value(self, detection: PIIDetection) -> str:
        """Mask PII value while preserving some structure."""
        value = detection.value
        
        if detection.category == PIICategory.EMAIL:
            parts = value.split("@")
            if len(parts) == 2:
                masked_name = parts[0][0] + "***" + parts[0][-1] if len(parts[0]) > 2 else "***"
                return f"{masked_name}@{parts[1]}"
        
        elif detection.category == PIICategory.PHONE:
            # Keep last 4 digits
            digits = re.sub(r"\D", "", value)
            if len(digits) >= 4:
                return f"***-***-{digits[-4:]}"
        
        elif detection.category == PIICategory.SSN:
            return "***-**-****"
        
        elif detection.category == PIICategory.CREDIT_CARD:
            # Keep last 4 digits
            digits = re.sub(r"\D", "", value)
            if len(digits) >= 4:
                return f"****-****-****-{digits[-4:]}"
        
        elif detection.category == PIICategory.IP_ADDRESS:
            parts = value.split(".")
            if len(parts) == 4:
                return f"{parts[0]}.{parts[1]}.*.*"
        
        # Default: mask all but first and last character
        if len(value) > 2:
            return value[0] + "*" * (len(value) - 2) + value[-1]
        elif len(value) > 0:
            return "*"
        return ""

    def add_pattern(
        self,
        category: PIICategory,
        pattern: str,
        confidence: float = 0.8,
    ):
        """Add a custom PII detection pattern."""
        if category not in self._patterns:
            self._patterns[category] = []
        self._patterns[category].append((pattern, confidence))

    def set_confidence_threshold(self, threshold: float):
        """Update confidence threshold."""
        self.confidence_threshold = threshold
