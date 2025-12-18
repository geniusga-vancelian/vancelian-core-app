"""
Unit tests for webhook security verification
"""

import pytest
import time
from app.utils.webhook_security import (
    verify_hmac_signature,
    verify_timestamp,
    verify_zand_webhook_security,
)


@pytest.fixture
def test_secret():
    """Test webhook secret"""
    return "test-webhook-secret-for-testing-only"


@pytest.fixture
def test_payload():
    """Test payload bytes"""
    return b'{"test":"data"}'


@pytest.fixture
def valid_signature(test_payload, test_secret):
    """Generate valid HMAC signature for test payload"""
    import hmac
    import hashlib
    return hmac.new(
        test_secret.encode('utf-8'),
        test_payload,
        hashlib.sha256
    ).hexdigest()


class TestHMACSignatureVerification:
    """Tests for HMAC signature verification"""
    
    def test_valid_signature_passes(self, test_payload, test_secret, valid_signature):
        """Valid signature should pass verification"""
        is_valid, error_code, error_details = verify_hmac_signature(
            payload_body=test_payload,
            signature_header=valid_signature,
            secret=test_secret,
        )
        assert is_valid is True
        assert error_code is None
        assert error_details is None
    
    def test_invalid_signature_fails(self, test_payload, test_secret):
        """Invalid signature should fail with WEBHOOK_INVALID_SIGNATURE"""
        invalid_signature = "invalid_signature_hex_string"
        is_valid, error_code, error_details = verify_hmac_signature(
            payload_body=test_payload,
            signature_header=invalid_signature,
            secret=test_secret,
        )
        assert is_valid is False
        assert error_code == "WEBHOOK_INVALID_SIGNATURE"
        assert error_details is not None
        assert "expected_length" in error_details
        assert "received_length" in error_details
        assert "hint" in error_details
    
    def test_missing_signature_fails(self, test_payload, test_secret):
        """Missing signature header should fail with WEBHOOK_MISSING_HEADER"""
        is_valid, error_code, error_details = verify_hmac_signature(
            payload_body=test_payload,
            signature_header="",
            secret=test_secret,
        )
        assert is_valid is False
        assert error_code == "WEBHOOK_MISSING_HEADER"
        assert error_details is not None
        assert "missing_header" in error_details
        assert error_details["missing_header"] == "X-Zand-Signature"
    
    def test_empty_secret_fails(self, test_payload):
        """Empty secret should fail with WEBHOOK_INVALID_SIGNATURE"""
        is_valid, error_code, error_details = verify_hmac_signature(
            payload_body=test_payload,
            signature_header="some_signature",
            secret="",
        )
        assert is_valid is False
        assert error_code == "WEBHOOK_INVALID_SIGNATURE"
        assert error_details is not None
        assert "reason" in error_details
    
    def test_signature_over_exact_bytes(self, test_secret):
        """Signature must be computed over exact raw bytes (canonical representation)"""
        # Same payload, different JSON serialization should produce same signature
        payload1 = b'{"test":"data"}'
        payload2 = b'{"test":"data"}'  # Same exact bytes
        
        import hmac
        import hashlib
        sig1 = hmac.new(test_secret.encode('utf-8'), payload1, hashlib.sha256).hexdigest()
        sig2 = hmac.new(test_secret.encode('utf-8'), payload2, hashlib.sha256).hexdigest()
        
        # Same bytes = same signature
        assert sig1 == sig2
        
        # Verify both signatures pass
        is_valid1, _, _ = verify_hmac_signature(payload1, sig1, test_secret)
        is_valid2, _, _ = verify_hmac_signature(payload2, sig2, test_secret)
        assert is_valid1 is True
        assert is_valid2 is True


class TestTimestampVerification:
    """Tests for timestamp verification"""
    
    def test_valid_timestamp_passes(self):
        """Valid timestamp within tolerance should pass"""
        current_time = int(time.time())
        timestamp_str = str(current_time)
        is_valid, error_code, error_details = verify_timestamp(
            timestamp_header=timestamp_str,
            tolerance_seconds=300,
        )
        assert is_valid is True
        assert error_code is None
        assert error_details is None
    
    def test_no_timestamp_passes(self):
        """No timestamp provided should pass (idempotency protection only)"""
        is_valid, error_code, error_details = verify_timestamp(
            timestamp_header=None,
            tolerance_seconds=300,
        )
        assert is_valid is True
        assert error_code is None
        assert error_details is None
    
    def test_invalid_timestamp_format_fails(self):
        """Invalid timestamp format should fail with WEBHOOK_INVALID_TIMESTAMP"""
        is_valid, error_code, error_details = verify_timestamp(
            timestamp_header="not-a-number",
            tolerance_seconds=300,
        )
        assert is_valid is False
        assert error_code == "WEBHOOK_INVALID_TIMESTAMP"
        assert error_details is not None
        assert "received" in error_details
        assert "hint" in error_details
    
    def test_timestamp_too_old_fails(self):
        """Timestamp outside tolerance (too old) should fail with WEBHOOK_TIMESTAMP_SKEW"""
        old_timestamp = int(time.time()) - 400  # 400 seconds ago (outside 300s tolerance)
        is_valid, error_code, error_details = verify_timestamp(
            timestamp_header=str(old_timestamp),
            tolerance_seconds=300,
        )
        assert is_valid is False
        assert error_code == "WEBHOOK_TIMESTAMP_SKEW"
        assert error_details is not None
        assert "time_delta_seconds" in error_details
        assert "max_skew_seconds" in error_details
        assert error_details["max_skew_seconds"] == 300
    
    def test_timestamp_too_new_fails(self):
        """Timestamp outside tolerance (too new) should fail with WEBHOOK_TIMESTAMP_SKEW"""
        future_timestamp = int(time.time()) + 400  # 400 seconds in future (outside 300s tolerance)
        is_valid, error_code, error_details = verify_timestamp(
            timestamp_header=str(future_timestamp),
            tolerance_seconds=300,
        )
        assert is_valid is False
        assert error_code == "WEBHOOK_TIMESTAMP_SKEW"
        assert error_details is not None
        assert "time_delta_seconds" in error_details


class TestCompleteWebhookSecurityVerification:
    """Tests for complete webhook security verification"""
    
    def test_missing_signature_header_fails(self, test_payload, monkeypatch):
        """Missing signature header should fail with WEBHOOK_MISSING_HEADER"""
        # Mock settings
        from app.infrastructure.settings import get_settings
        settings = get_settings()
        monkeypatch.setattr(settings, "ZAND_WEBHOOK_SECRET", "test-secret")
        monkeypatch.setattr(settings, "ZAND_WEBHOOK_TOLERANCE_SECONDS", 300)
        
        is_valid, error_code, error_details = verify_zand_webhook_security(
            payload_body=test_payload,
            signature_header=None,
            timestamp_header=None,
        )
        assert is_valid is False
        assert error_code == "WEBHOOK_MISSING_HEADER"
        assert error_details is not None
        assert "missing_header" in error_details
    
    def test_valid_webhook_passes(self, test_payload, test_secret, valid_signature, monkeypatch):
        """Valid webhook with signature and timestamp should pass"""
        # Mock settings
        from app.infrastructure.settings import get_settings
        settings = get_settings()
        monkeypatch.setattr(settings, "ZAND_WEBHOOK_SECRET", test_secret)
        monkeypatch.setattr(settings, "ZAND_WEBHOOK_TOLERANCE_SECONDS", 300)
        
        current_time = str(int(time.time()))
        is_valid, error_code, error_details = verify_zand_webhook_security(
            payload_body=test_payload,
            signature_header=valid_signature,
            timestamp_header=current_time,
        )
        assert is_valid is True
        assert error_code is None
        assert error_details is None

