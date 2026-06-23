"""Security Proxy - sanitizes prompts before model inference and responses after."""

from typing import Optional
from .pii_scrubber import PIIScrubber, ScrubResult
from .privacy_firewall import PrivacyFirewall, FirewallResult


class SecurityProxy:
    """
    Proxy that sanitizes data before and after model inference.
    
    Pipeline:
    1. Scrub PII from user prompts
    2. Check against privacy firewall
    3. Allow/block the request
    4. Scan responses for leaked secrets
    """

    def __init__(
        self,
        scrub_pii: bool = True,
        block_credentials: bool = True,
        block_internal_urls: bool = True,
        confidence_threshold: float = 0.7,
        replacement_strategy: str = "mask",
    ):
        self.scrubber = PIIScrubber(
            confidence_threshold=confidence_threshold,
            replacement_strategy=replacement_strategy,
        )
        self.firewall = PrivacyFirewall(
            block_pii=scrub_pii,
            block_credentials=block_credentials,
            block_internal_urls=block_internal_urls,
        )
        self._enabled = True

    def sanitize_prompt(self, prompt: str) -> tuple[bool, str, dict]:
        """
        Sanitize a prompt before sending to model.
        
        Returns:
            Tuple of (allowed, sanitized_prompt, metadata)
        """
        if not self._enabled:
            return True, prompt, {"scrubbed": False, "firewall": False}
        
        metadata = {
            "scrubbed": False,
            "firewall": False,
            "pii_found": 0,
            "firewall_blocked": False,
        }
        
        # Step 1: Check firewall first (before scrubbing, as scrubbing may alter patterns)
        firewall_result = self.firewall.check(prompt)
        if not firewall_result.allowed:
            metadata["firewall"] = True
            metadata["firewall_blocked"] = True
            metadata["blocked_reasons"] = [r.value for r in firewall_result.blocked_reasons]
            return False, prompt, metadata
        
        # Step 2: Scrub PII
        scrubbed, scrub_result = self.scrubber.scrub(prompt)
        if scrub_result.pii_found > 0:
            metadata["scrubbed"] = True
            metadata["pii_found"] = scrub_result.pii_found
            prompt = scrubbed
        
        return True, prompt, metadata

    def sanitize_response(self, response: str) -> tuple[str, dict]:
        """
        Scan and sanitize a model response.
        
        Returns:
            Tuple of (sanitized_response, metadata)
        """
        if not self._enabled:
            return response, {"scanned": False}
        
        metadata = {
            "scanned": True,
            "issues_found": 0,
        }
        
        # Scan for leaked secrets
        firewall_result = self.firewall.check(response)
        
        if not firewall_result.allowed:
            # Redact sensitive parts
            for match in firewall_result.blocked_matches:
                response = response.replace(match, "[REDACTED]")
            metadata["issues_found"] = len(firewall_result.blocked_matches)
        
        # Scrub any residual PII
        scrubbed, scrub_result = self.scrubber.scrub(response)
        if scrub_result.pii_found > 0:
            response = scrubbed
            metadata["pii_found"] = scrub_result.pii_found
        
        return response, metadata

    def enable(self):
        """Enable the security proxy."""
        self._enabled = True

    def disable(self):
        """Disable the security proxy (for trusted environments)."""
        self._enabled = False

    def is_enabled(self) -> bool:
        """Check if proxy is enabled."""
        return self._enabled

    def get_stats(self) -> dict:
        """Get proxy statistics."""
        return {
            "enabled": self._enabled,
            "scrubber": {
                "confidence_threshold": self.scrubber.confidence_threshold,
                "replacement_strategy": self.scrubber.replacement_strategy,
            },
            "firewall": {
                "block_pii": self.firewall.block_pii,
                "block_credentials": self.firewall.block_credentials,
                "block_internal_urls": self.firewall.block_internal_urls,
                "custom_rules": len(self.firewall._custom_rules),
            },
        }
