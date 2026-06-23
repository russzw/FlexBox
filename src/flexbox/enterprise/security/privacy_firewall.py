"""Privacy Firewall - blocks sensitive data from leaving the local network."""

import re
from typing import Optional
from dataclasses import dataclass, field
from enum import Enum


class BlockReason(Enum):
    """Reasons for blocking data."""
    PII_DETECTED = "pii_detected"
    CREDENTIAL_DETECTED = "credential_detected"
    SECRET_DETECTED = "secret_detected"
    INTERNAL_URL = "internal_url"
    CUSTOM_RULE = "custom_rule"


@dataclass
class FirewallRule:
    """Custom firewall rule."""
    name: str
    pattern: str
    reason: BlockReason
    confidence: float = 0.9
    enabled: bool = True


@dataclass
class FirewallResult:
    """Result of firewall check."""
    allowed: bool
    blocked_reasons: list[BlockReason] = field(default_factory=list)
    blocked_matches: list[str] = field(default_factory=list)
    checks_passed: int = 0
    checks_failed: int = 0


class PrivacyFirewall:
    """
    Privacy firewall that blocks sensitive data from leaving the network.
    
    Features:
    - PII detection and blocking
    - Credential and secret detection
    - Internal URL blocking
    - Custom rule support
    - Whitelist/blacklist patterns
    """

    # Built-in sensitive patterns
    SENSITIVE_PATTERNS = {
        BlockReason.CREDENTIAL_DETECTED: [
            (r"(?i)(?:api[_-]?key|apikey)\s*[:=]\s*['\"]?[A-Za-z0-9\-_]{20,}['\"]?", 0.9),
            (r"(?i)(?:secret|token)\s*[:=]\s*['\"]?[A-Za-z0-9\-_]{20,}['\"]?", 0.85),
            (r"(?i)(?:password|passwd|pwd)\s*[:=]\s*['\"]?[^\s'\"]{8,}['\"]?", 0.9),
            (r"(?i)bearer\s+[A-Za-z0-9\-_.]+", 0.9),
            (r"(?:sk|pk|rk|token|key)_[A-Za-z0-9]{20,}", 0.85),  # Raw API keys with common prefixes
        ],
        BlockReason.SECRET_DETECTED: [
            (r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----", 0.99),
            (r"(?i)aws[_-]?(?:access[_-]?key[_-]?id|secret[_-]?access[_-]?key)\s*[:=]?\s*['\"]?[A-Za-z0-9/+=]{40}['\"]?", 0.95),
            (r"(?i)github[_-]?(?:token|pat)\s*[:=]?\s*['\"]?ghp_[A-Za-z0-9]{36,}['\"]?", 0.95),
            (r"(?i)slack[_-]?(?:token|bot[_-]?token)\s*[:=]?\s*['\"]?xox[bpoas]-[A-Za-z0-9\-]+['\"]?", 0.9),
        ],
        BlockReason.INTERNAL_URL: [
            (r"(?i)https?://(?:localhost|127\.0\.0\.1|10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+|172\.(?:1[6-9]|2\d|3[01])\.\d+\.\d+)(?::\d+)?/?", 0.9),
            (r"(?i)https?://[a-z0-9\-]+\.internal(?::\d+)?/?", 0.85),
        ],
    }

    def __init__(
        self,
        custom_rules: Optional[list[FirewallRule]] = None,
        whitelist_patterns: Optional[list[str]] = None,
        block_pii: bool = True,
        block_credentials: bool = True,
        block_internal_urls: bool = True,
    ):
        self.block_pii = block_pii
        self.block_credentials = block_credentials
        self.block_internal_urls = block_internal_urls
        self._custom_rules = custom_rules or []
        self._whitelist_patterns = whitelist_patterns or []
        
        # Compile all patterns
        self._compiled_rules: list[tuple[str, re.Pattern, BlockReason, float]] = []
        self._compile_rules()

    def _compile_rules(self):
        """Compile all detection rules."""
        for reason, pattern_list in self.SENSITIVE_PATTERNS.items():
            for pattern, confidence in pattern_list:
                compiled = re.compile(pattern)
                self._compiled_rules.append(("builtin", compiled, reason, confidence))
        
        for rule in self._custom_rules:
            if rule.enabled:
                compiled = re.compile(rule.pattern)
                self._compiled_rules.append((rule.name, compiled, rule.reason, rule.confidence))

    def check(self, text: str) -> FirewallResult:
        """
        Check if text is safe to send externally.
        
        Args:
            text: Text to check
            
        Returns:
            FirewallResult with allowed=True/False
        """
        blocked_reasons = []
        blocked_matches = []
        
        # Check whitelist first
        for whitelist_pattern in self._whitelist_patterns:
            if re.search(whitelist_pattern, text):
                return FirewallResult(
                    allowed=True,
                    checks_passed=len(self._compiled_rules),
                )
        
        for name, compiled, reason, confidence in self._compiled_rules:
            # Skip disabled categories
            if reason == BlockReason.PII_DETECTED and not self.block_pii:
                continue
            if reason == BlockReason.CREDENTIAL_DETECTED and not self.block_credentials:
                continue
            if reason == BlockReason.INTERNAL_URL and not self.block_internal_urls:
                continue
            
            matches = compiled.findall(text)
            if matches:
                for match in matches:
                    match_str = match if isinstance(match, str) else match[0]
                    if confidence >= 0.8:
                        blocked_reasons.append(reason)
                        blocked_matches.append(match_str)
        
        allowed = len(blocked_reasons) == 0
        
        return FirewallResult(
            allowed=allowed,
            blocked_reasons=list(set(blocked_reasons)),
            blocked_matches=blocked_matches,
            checks_passed=len(self._compiled_rules) - len(blocked_reasons),
            checks_failed=len(blocked_reasons),
        )

    def add_rule(self, rule: FirewallRule):
        """Add a custom firewall rule."""
        self._custom_rules.append(rule)
        compiled = re.compile(rule.pattern)
        self._compiled_rules.append((rule.name, compiled, rule.reason, rule.confidence))

    def remove_rule(self, name: str):
        """Remove a custom rule by name."""
        self._custom_rules = [r for r in self._custom_rules if r.name != name]
        self._compiled_rules = [(n, p, r, c) for n, p, r, c in self._compiled_rules if n != name]

    def add_whitelist(self, pattern: str):
        """Add a whitelist pattern."""
        self._whitelist_patterns.append(pattern)

    def scan_prompt(self, prompt: str) -> tuple[bool, list[str]]:
        """
        Scan a prompt before sending to model.
        
        Returns:
            Tuple of (safe, list of issues)
        """
        result = self.check(prompt)
        
        issues = []
        for match in result.blocked_matches:
            issues.append(f"Blocked: {match[:30]}...")
        
        return result.allowed, issues

    def scan_response(self, response: str) -> tuple[bool, list[str]]:
        """
        Scan a model response before returning to user.
        
        Returns:
            Tuple of (safe, list of issues)
        """
        result = self.check(response)
        
        issues = []
        for match in result.blocked_matches:
            issues.append(f"Sensitive in response: {match[:30]}...")
        
        return result.allowed, issues
