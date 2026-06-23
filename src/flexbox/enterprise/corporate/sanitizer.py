"""Secret Sanitizer - scrubs sensitive data from training pipelines."""

import re
from typing import Optional
from dataclasses import dataclass, field


@dataclass
class SanitizationResult:
    """Result of sanitization operation."""
    original_length: int
    sanitized_length: int
    secrets_found: int
    secrets_removed: int
    patterns_matched: dict[str, int] = field(default_factory=dict)


class SecretSanitizer:
    """
    Scrubs secrets, PII, and sensitive data from code and text.
    
    Detects and removes:
    - API keys and tokens
    - Passwords and credentials
    - Database connection strings
    - Private keys and certificates
    - Email addresses
    - Phone numbers
    - Social security numbers
    - Credit card numbers
    - Internal URLs and IPs
    """

    # Pattern definitions
    PATTERNS = {
        "api_key": [
            r"(?i)(api[_-]?key|apikey)\s*[:=]\s*['\"]([^'\"]+)['\"]",
            r"(?i)(secret|token)\s*[:=]\s*['\"]([^'\"]+)['\"]",
            r"(?i)bearer\s+[A-Za-z0-9\-._~+/]+=*",
        ],
        "aws_key": [
            r"AKIA[0-9A-Z]{16}",
            r"(?i)aws[_-]?(access[_-]?key[_-]?id|secret[_-]?access[_-]?key)\s*[:=]\s*['\"]?([A-Za-z0-9/+=]+)['\"]?",
        ],
        "password": [
            r"(?i)(password|passwd|pwd)\s*[:=]\s*['\"]([^'\"]+)['\"]",
            r"(?i)(secret|credential)\s*[:=]\s*['\"]([^'\"]+)['\"]",
        ],
        "database_url": [
            r"(?i)(postgres|mysql|mongodb|redis)://[^\s'\"]+",
            r"(?i)connection[_-]?string\s*[:=]\s*['\"]([^'\"]+)['\"]",
        ],
        "private_key": [
            r"-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----",
            r"(?i)private[_-]?key\s*[:=]\s*['\"]([^'\"]+)['\"]",
        ],
        "email": [
            r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
        ],
        "phone": [
            r"(?i)(\+?1?[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}",
        ],
        "ssn": [
            r"\d{3}-\d{2}-\d{4}",
        ],
        "credit_card": [
            r"\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}",
        ],
        "ip_address": [
            r"(?i)(localhost|127\.0\.0\.1|10\.\d{1,3}\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3}|172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})",
        ],
        "internal_url": [
            r"(?i)https?://(?:internal|dev|staging|stage|test|qa|uat)\.[^\s'\"]+",
            r"(?i)https?://(?:localhost|127\.0\.0\.1|10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+)(?::\d+)?[^\s'\"]*",
        ],
        "env_var": [
            r"(?i)(NEXT_PUBLIC_|VITE_|REACT_APP_|AWS_|GCP_|AZURE_)[A-Z_]+",
        ],
    }

    # Replacement placeholders
    REPLACEMENTS = {
        "api_key": "[REDACTED_API_KEY]",
        "aws_key": "[REDACTED_AWS_KEY]",
        "password": "[REDACTED_PASSWORD]",
        "database_url": "[REDACTED_DB_URL]",
        "private_key": "[REDACTED_PRIVATE_KEY]",
        "email": "[REDACTED_EMAIL]",
        "phone": "[REDACTED_PHONE]",
        "ssn": "[REDACTED_SSN]",
        "credit_card": "[REDACTED_CREDIT_CARD]",
        "ip_address": "[REDACTED_IP]",
        "internal_url": "[REDACTED_INTERNAL_URL]",
        "env_var": "[REDACTED_ENV_VAR]",
    }

    def __init__(self, custom_patterns: Optional[dict[str, list[str]]] = None):
        self.patterns = self.PATTERNS.copy()
        if custom_patterns:
            self.patterns.update(custom_patterns)
        
        # Compile patterns
        self._compiled = {}
        for category, pattern_list in self.patterns.items():
            self._compiled[category] = [
                re.compile(p) for p in pattern_list
            ]

    def sanitize(self, text: str) -> tuple[str, SanitizationResult]:
        """
        Sanitize text by removing secrets and sensitive data.
        
        Args:
            text: Input text to sanitize
            
        Returns:
            Tuple of (sanitized_text, result)
        """
        original_length = len(text)
        sanitized = text
        total_secrets = 0
        total_removed = 0
        patterns_matched = {}

        for category, compiled_patterns in self._compiled.items():
            for pattern in compiled_patterns:
                matches = pattern.findall(sanitized)
                
                if matches:
                    count = len(matches)
                    total_secrets += count
                    patterns_matched[category] = patterns_matched.get(category, 0) + count
                    
                    # Replace matches
                    replacement = self.REPLACEMENTS.get(category, "[REDACTED]")
                    sanitized = pattern.sub(replacement, sanitized)
                    total_removed += count

        result = SanitizationResult(
            original_length=original_length,
            sanitized_length=len(sanitized),
            secrets_found=total_secrets,
            secrets_removed=total_removed,
            patterns_matched=patterns_matched,
        )

        return sanitized, result

    def sanitize_code(self, code: str, language: str = "unknown") -> tuple[str, SanitizationResult]:
        """
        Sanitize code with language-aware handling.
        
        Args:
            code: Source code to sanitize
            language: Programming language
            
        Returns:
            Tuple of (sanitized_code, result)
        """
        # First, apply general sanitization
        sanitized, result = self.sanitize(code)
        
        # Language-specific patterns
        if language in ("javascript", "typescript", "jsx", "tsx"):
            # Check for hardcoded secrets in JS/TS
            js_patterns = [
                (r"(?i)const\s+\w+\s*=\s*['\"]([A-Za-z0-9\-._~+/]+=*)['\"]", "hardcoded_secret"),
                (r"(?i)process\.env\.\w+", "env_access"),
            ]
            
            for pattern_str, category in js_patterns:
                pattern = re.compile(pattern_str)
                matches = pattern.findall(sanitized)
                if matches:
                    result.secrets_found += len(matches)
                    result.patterns_matched[category] = len(matches)
                    sanitized = pattern.sub(f"[REDACTED_{category.upper()}]", sanitized)
        
        elif language in ("python",):
            # Check for hardcoded secrets in Python
            py_patterns = [
                (r"(?i)\w+\s*=\s*['\"]([A-Za-z0-9\-._~+/]+=*)['\"]", "hardcoded_secret"),
                (r"(?i)os\.environ\.get\(['\"]\w+['\"]\)", "env_access"),
            ]
            
            for pattern_str, category in py_patterns:
                pattern = re.compile(pattern_str)
                matches = pattern.findall(sanitized)
                if matches:
                    result.secrets_found += len(matches)
                    result.patterns_matched[category] = len(matches)
                    sanitized = pattern.sub(f"[REDACTED_{category.upper()}]", sanitized)
        
        result.sanitized_length = len(sanitized)
        return sanitized, result

    def detect_secrets(self, text: str) -> dict[str, list[str]]:
        """
        Detect secrets without removing them.
        
        Returns:
            Dictionary of category -> list of found secrets
        """
        found = {}
        
        for category, compiled_patterns in self._compiled.items():
            category_matches = []
            
            for pattern in compiled_patterns:
                matches = pattern.findall(text)
                if matches:
                    # Flatten matches
                    for match in matches:
                        if isinstance(match, tuple):
                            category_matches.extend(match)
                        else:
                            category_matches.append(match)
            
            if category_matches:
                found[category] = category_matches
        
        return found

    def add_pattern(self, category: str, pattern: str, replacement: Optional[str] = None):
        """Add a custom detection pattern."""
        if category not in self.patterns:
            self.patterns[category] = []
            self._compiled[category] = []
        
        self.patterns[category].append(pattern)
        self._compiled[category].append(re.compile(pattern))
        
        if replacement:
            self.REPLACEMENTS[category] = replacement
