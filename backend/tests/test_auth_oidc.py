"""
Tests for OIDC authentication
"""

import pytest
from fastapi.testclient import TestClient
from uuid import uuid4

from tests.auth_utils import create_test_jwt, get_test_public_key_pem
from app.auth.oidc import OIDCVerifier, Principal
from unittest.mock import patch, Mock


def test_create_test_jwt():
    """Test JWT creation utility"""
    token = create_test_jwt(
        subject="test-user-123",
        email="test@example.com",
        roles=["USER"],
    )
    
    assert token is not None
    assert isinstance(token, str)
    assert len(token) > 0


@pytest.fixture
def mock_jwks_client():
    """Mock JWKS client for tests"""
    from tests.auth_utils import get_test_public_key_pem
    from cryptography.hazmat.primitives import serialization
    
    # Create mock JWKS response
    public_key_pem = get_test_public_key_pem()
    
    # Parse public key to get modulus and exponent
    from cryptography.hazmat.primitives.serialization import load_pem_public_key
    public_key = load_pem_public_key(public_key_pem.encode())
    
    # Mock JWKS client
    mock_client = Mock()
    mock_signing_key = Mock()
    mock_signing_key.key = public_key
    
    def get_signing_key(kid):
        return mock_signing_key
    
    mock_client.get_signing_key = get_signing_key
    
    return mock_client


def test_verify_test_jwt_token(mock_jwks_client):
    """Test JWT verification with test token"""
    # Create test token
    token = create_test_jwt(
        subject="test-user-123",
        email="test@example.com",
        roles=["USER", "ADMIN"],
        audience="test-audience",
        issuer="https://test-issuer.example.com",
    )
    
    # Mock OIDC verifier
    with patch('app.auth.oidc.PyJWKClient') as mock_pyjwk:
        mock_pyjwk.return_value = mock_jwks_client
        
        # Get verifier (will use mocked JWKS client)
        verifier = OIDCVerifier()
        verifier._jwks_client = mock_jwks_client
        
        # Verify token
        principal = verifier.verify_token(token)
        
        assert principal.subject == "test-user-123"
        assert principal.email == "test@example.com"
        assert "USER" in principal.roles
        assert "ADMIN" in principal.roles


def test_api_endpoint_requires_auth(client, test_user):
    """Test that /api/v1/wallet requires authentication"""
    # Call without token
    response = client.get("/api/v1/wallet?currency=AED")
    
    assert response.status_code == 401
    assert "error" in response.json()
    assert response.json()["error"]["code"] == "AUTH_REQUIRED"


def test_api_endpoint_with_valid_token(client, test_user, mock_jwks_client):
    """Test /api/v1/wallet with valid JWT token"""
    from tests.auth_utils import create_test_jwt
    from app.auth.oidc import get_verifier
    
    # Create token for test user
    token = create_test_jwt(
        subject=str(test_user.id),
        email=test_user.email,
        roles=["USER"],
    )
    
    # Mock verifier for this request
    with patch('app.auth.dependencies.get_verifier') as mock_get_verifier:
        verifier = OIDCVerifier()
        verifier._jwks_client = mock_jwks_client
        mock_get_verifier.return_value = verifier
        
        # Call with token
        response = client.get(
            "/api/v1/wallet?currency=AED",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Should succeed (200 or 404 if user has no wallet)
        assert response.status_code in [200, 404]


def test_admin_endpoint_requires_role(client, test_user, mock_jwks_client):
    """Test that /admin/v1/* requires ADMIN/COMPLIANCE/OPS role"""
    from tests.auth_utils import create_test_jwt
    from app.auth.oidc import get_verifier
    
    # Create token with USER role (should be denied)
    token = create_test_jwt(
        subject=str(test_user.id),
        email=test_user.email,
        roles=["USER"],
    )
    
    # Mock verifier
    with patch('app.auth.dependencies.get_verifier') as mock_get_verifier:
        verifier = OIDCVerifier()
        verifier._jwks_client = mock_jwks_client
        mock_get_verifier.return_value = verifier
        
        # Call admin endpoint with USER token (should be 403)
        response = client.post(
            "/admin/v1/compliance/release-funds",
            json={
                "transaction_id": str(uuid4()),
                "amount": "1000.00",
                "reason": "test",
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 403
        assert "error" in response.json()
        assert response.json()["error"]["code"] == "FORBIDDEN"


def test_admin_endpoint_with_compliance_role(client, test_user, mock_jwks_client):
    """Test /admin/v1/* with COMPLIANCE role"""
    from tests.auth_utils import create_test_jwt
    from app.auth.oidc import get_verifier
    
    # Create token with COMPLIANCE role
    token = create_test_jwt(
        subject=str(test_user.id),
        email=test_user.email,
        roles=["COMPLIANCE"],
    )
    
    # Mock verifier
    with patch('app.auth.dependencies.get_verifier') as mock_get_verifier:
        verifier = OIDCVerifier()
        verifier._jwks_client = mock_jwks_client
        mock_get_verifier.return_value = verifier
        
        # Call admin endpoint with COMPLIANCE token
        # Should not be 403 (may be 404 if transaction doesn't exist, but not 403)
        response = client.post(
            "/admin/v1/compliance/release-funds",
            json={
                "transaction_id": str(uuid4()),
                "amount": "1000.00",
                "reason": "test",
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Should not be forbidden (may be 404 if transaction doesn't exist)
        assert response.status_code != 403


def test_webhook_no_auth_required(client):
    """Test that webhooks don't require OIDC auth (only HMAC)"""
    # Webhook endpoint should not require Authorization header
    # (it uses HMAC signature verification instead)
    # This test ensures webhooks still work without OIDC
    
    response = client.post(
        "/webhooks/v1/zand/deposit",
        json={
            "provider_event_id": "test-event-123",
            "iban": "AE123456789012345678901",
            "user_id": str(uuid4()),
            "amount": "1000.00",
            "currency": "AED",
            "occurred_at": "2025-12-18T10:00:00Z",
        },
        headers={
            "X-Zand-Signature": "test-signature-placeholder",
        },
    )
    
    # Should not be 401 Unauthorized (OIDC-related)
    # May be 401 if HMAC verification fails, but not due to missing OIDC token
    assert response.status_code != 401 or "AUTH_REQUIRED" not in str(response.json())


