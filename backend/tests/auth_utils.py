"""
Utilities for testing OIDC authentication
"""

import time
import jwt
from typing import Dict, Any, List, Optional
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


# Test private key (RSA 2048) - ONLY FOR TESTS
_TEST_PRIVATE_KEY = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,
)

_TEST_PUBLIC_KEY = _TEST_PRIVATE_KEY.public_key()


def get_test_public_key_pem() -> str:
    """Get test public key in PEM format (for JWKS)"""
    return _TEST_PUBLIC_KEY.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode('utf-8')


def get_test_private_key_pem() -> str:
    """Get test private key in PEM format"""
    return _TEST_PRIVATE_KEY.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode('utf-8')


def create_test_jwt(
    subject: str,
    email: Optional[str] = None,
    roles: Optional[List[str]] = None,
    audience: str = "test-audience",
    issuer: str = "https://test-issuer.example.com",
    expires_in: int = 3600,
    additional_claims: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Create a test JWT token for testing.
    
    Args:
        subject: OIDC 'sub' claim
        email: Email claim (optional)
        roles: List of role strings (will be set in realm_access.roles and roles claim)
        audience: Audience claim (default: "test-audience")
        issuer: Issuer claim (default: "https://test-issuer.example.com")
        expires_in: Token expiration in seconds (default: 3600)
        additional_claims: Additional claims to include in token
        
    Returns:
        JWT token string
    """
    now = int(time.time())
    
    claims = {
        "sub": subject,
        "iss": issuer,
        "aud": audience,
        "iat": now,
        "exp": now + expires_in,
        "nbf": now,
    }
    
    if email:
        claims["email"] = email
        claims["preferred_username"] = email
    
    if roles:
        # Set roles in multiple places (Zitadel-compatible)
        claims["roles"] = roles
        claims["realm_access"] = {"roles": roles}
        claims["resource_access"] = {
            audience: {"roles": roles}
        }
    
    if additional_claims:
        claims.update(additional_claims)
    
    # Sign token with test private key
    token = jwt.encode(
        claims,
        _TEST_PRIVATE_KEY,
        algorithm="RS256",
        headers={"kid": "test-key-id"},
    )
    
    return token


def create_test_jwt_for_user(
    user_id: str,
    email: str,
    role: str = "USER",
    **kwargs,
) -> str:
    """
    Convenience function to create a test JWT for a user.
    
    Args:
        user_id: User ID (used as subject)
        email: User email
        role: User role (default: "USER")
        **kwargs: Additional arguments passed to create_test_jwt
        
    Returns:
        JWT token string
    """
    return create_test_jwt(
        subject=user_id,
        email=email,
        roles=[role],
        **kwargs,
    )


