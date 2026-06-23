"""Phase 3 validation tests - Enterprise Tier."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


def test_phase3_headless_runtime():
    """Test headless runtime in different modes."""
    from flexbox.enterprise.headless import HeadlessRuntime, RuntimeMode, RuntimeConfig
    
    # Test local mode
    config = RuntimeConfig(mode=RuntimeMode.LOCAL)
    runtime = HeadlessRuntime(config=config)
    assert runtime.config.mode == RuntimeMode.LOCAL
    
    # Test remote mode
    config = RuntimeConfig(mode=RuntimeMode.REMOTE, gateway_url="https://gateway.corp.com")
    runtime = HeadlessRuntime(config=config)
    assert runtime.config.mode == RuntimeMode.REMOTE
    assert runtime.config.gateway_url == "https://gateway.corp.com"
    
    # Test hybrid mode
    config = RuntimeConfig(mode=RuntimeMode.HYBRID)
    runtime = HeadlessRuntime(config=config)
    assert runtime.config.mode == RuntimeMode.HYBRID
    
    # Test air-gapped mode
    config = RuntimeConfig(mode=RuntimeMode.AIR_GAPPED)
    runtime = HeadlessRuntime(config=config)
    assert runtime.config.mode == RuntimeMode.AIR_GAPPED
    
    return True


def test_phase3_gateway():
    """Test FlexCorp Gateway."""
    from flexbox.enterprise.gateway import FlexCorpGateway, GatewayConfig
    
    config = GatewayConfig(host="127.0.0.1", port=8080)
    gateway = FlexCorpGateway(config=config)
    assert gateway.config.host == "127.0.0.1"
    assert gateway.config.port == 8080
    
    # Test status
    status = gateway.get_status()
    assert "status" in status
    assert "models" in status
    
    return True


def test_phase3_corporate_pipeline():
    """Test corporate pipeline."""
    from flexbox.enterprise.corporate.pipeline import CorporatePipeline, PipelineConfig
    
    config = PipelineConfig(
        org_name="TestCorp",
        repo_paths=["."],
        output_dir="test_corporate_output",
    )
    pipeline = CorporatePipeline(config)
    
    # Test report generation
    report = pipeline.generate_report()
    assert report["org_name"] == "TestCorp"
    assert report["adapter_name"] == "flexcorp"
    
    return True


def test_phase3_pii_scrubber():
    """Test PII scrubber."""
    from flexbox.enterprise.security.pii_scrubber import PIIScrubber, PIICategory
    
    scrubber = PIIScrubber(confidence_threshold=0.7)
    
    # Test email detection
    text = "Contact me at john.doe@example.com for details"
    scrubbed, result = scrubber.scrub(text)
    assert result.pii_found > 0
    assert "john.doe@example.com" not in scrubbed
    
    # Test phone detection
    text = "Call me at (555) 123-4567"
    scrubbed, result = scrubber.scrub(text)
    assert result.pii_found > 0
    
    # Test SSN detection
    text = "SSN: 123-45-6789"
    scrubbed, result = scrubber.scrub(text)
    assert result.pii_found > 0
    assert "123-45-6789" not in scrubbed
    
    # Test credit card detection
    text = "Card: 4111-1111-1111-1111"
    scrubbed, result = scrubber.scrub(text)
    assert result.pii_found > 0
    
    # Test IP address detection
    text = "Server at 192.168.1.100"
    scrubbed, result = scrubber.scrub(text)
    assert result.pii_found > 0
    
    # Test custom pattern
    scrubber.add_pattern(
        PIICategory.EMAIL,
        r"(?i)confidential@[a-z]+\.com",
        confidence=0.95,
    )
    text = "Email confidential@test.com"
    scrubbed, result = scrubber.scrub(text)
    assert result.pii_found > 0
    
    return True


def test_phase3_privacy_firewall():
    """Test privacy firewall."""
    from flexbox.enterprise.security.privacy_firewall import PrivacyFirewall, BlockReason, FirewallRule
    
    firewall = PrivacyFirewall()
    
    # Test credential blocking
    result = firewall.check("api_key=sk_1234567890123456789012345")
    assert not result.allowed
    assert BlockReason.CREDENTIAL_DETECTED in result.blocked_reasons
    
    # Test secret blocking
    result = firewall.check("-----BEGIN RSA PRIVATE KEY-----")
    assert not result.allowed
    assert BlockReason.SECRET_DETECTED in result.blocked_reasons
    
    # Test internal URL blocking
    result = firewall.check("http://192.168.1.100:8080/api")
    assert not result.allowed
    assert BlockReason.INTERNAL_URL in result.blocked_reasons
    
    # Test safe text
    result = firewall.check("Hello, how are you today?")
    assert result.allowed
    
    # Test custom rule
    custom_rule = FirewallRule(
        name="no_internal_emails",
        pattern=r"(?i)@internal\.corp\.com",
        reason=BlockReason.CUSTOM_RULE,
        confidence=0.95,
    )
    firewall.add_rule(custom_rule)
    result = firewall.check("Send to user@internal.corp.com")
    assert not result.allowed
    assert BlockReason.CUSTOM_RULE in result.blocked_reasons
    
    # Test whitelist
    firewall.add_whitelist(r"(?i)approved_pattern")
    result = firewall.check("This contains approved_pattern")
    assert result.allowed
    
    return True


def test_phase3_security_proxy():
    """Test security proxy."""
    from flexbox.enterprise.security.proxy import SecurityProxy
    
    proxy = SecurityProxy(scrub_pii=True, block_credentials=True)
    
    # Test safe prompt
    allowed, prompt, meta = proxy.sanitize_prompt("Create a React button component")
    assert allowed
    assert not meta["firewall_blocked"]
    
    # Test credential in prompt
    allowed, prompt, meta = proxy.sanitize_prompt("api_key=secret123456789012345")
    assert not allowed
    assert meta["firewall_blocked"]
    
    # Test PII in prompt
    allowed, prompt, meta = proxy.sanitize_prompt("My email is john@test.com")
    assert allowed
    assert meta["pii_found"] > 0
    
    # Test response scanning
    safe_response, meta = proxy.sanitize_response("Hello! Here's the code...")
    assert meta["scanned"]
    
    # Test response with secrets
    unsafe_response, meta = proxy.sanitize_response("Here is the API key: sk_1234567890123456789012345")
    assert meta["issues_found"] > 0
    
    # Test disable/enable
    proxy.disable()
    assert not proxy.is_enabled()
    allowed, _, _ = proxy.sanitize_prompt("api_key=secret123456789012345")
    assert allowed  # Should be allowed when disabled
    
    proxy.enable()
    assert proxy.is_enabled()
    
    # Test stats
    stats = proxy.get_stats()
    assert "enabled" in stats
    assert "scrubber" in stats
    assert "firewall" in stats
    
    return True


def test_phase3_integration():
    """Test Phase 3 integration."""
    from flexbox.enterprise.headless import HeadlessRuntime, RuntimeMode, RuntimeConfig
    from flexbox.enterprise.gateway import FlexCorpGateway, GatewayConfig
    from flexbox.enterprise.security.proxy import SecurityProxy
    from flexbox.enterprise.corporate.pipeline import CorporatePipeline, PipelineConfig
    
    # Create components
    runtime_config = RuntimeConfig(mode=RuntimeMode.LOCAL)
    runtime = HeadlessRuntime(config=runtime_config)
    
    gateway_config = GatewayConfig(host="127.0.0.1", port=8080)
    gateway = FlexCorpGateway(config=gateway_config)
    
    security = SecurityProxy()
    
    # Test pipeline config
    pipeline_config = PipelineConfig(
        org_name="IntegrationTest",
        repo_paths=["."],
        output_dir="test_integration_output",
    )
    pipeline = CorporatePipeline(pipeline_config)
    
    # Verify all components work together
    assert runtime.config.mode == RuntimeMode.LOCAL
    assert gateway.config.port == 8080
    assert security.is_enabled()
    assert pipeline.config.org_name == "IntegrationTest"
    
    return True


def run_phase3_tests():
    """Run all Phase 3 tests."""
    tests = [
        ("HeadlessRuntime", test_phase3_headless_runtime),
        ("FlexCorpGateway", test_phase3_gateway),
        ("CorporatePipeline", test_phase3_corporate_pipeline),
        ("PIIScrubber", test_phase3_pii_scrubber),
        ("PrivacyFirewall", test_phase3_privacy_firewall),
        ("SecurityProxy", test_phase3_security_proxy),
        ("Phase 3 Integration", test_phase3_integration),
    ]
    
    passed = 0
    failed = 0
    
    print("\n" + "=" * 60)
    print("PHASE 3 VALIDATION: Enterprise Tier")
    print("=" * 60)
    
    for name, test_fn in tests:
        try:
            result = test_fn()
            if result:
                print(f"  [PASS] {name}")
                passed += 1
            else:
                print(f"  [FAIL] {name}")
                failed += 1
        except Exception as e:
            print(f"  [FAIL] {name}: {e}")
            failed += 1
    
    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_phase3_tests()
    sys.exit(0 if success else 1)
