"""
OIDC JWT verification and user provisioning
Zitadel-compatible implementation
"""

import time
import json
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime, timezone
import logging

import jwt
import httpx
from jwt import PyJWKClient
from jwt.exceptions import InvalidTokenError, ExpiredSignatureError, InvalidSignatureError

from app.infrastructure.settings import get_settings

logger = logging.getLogger(__name__)

# In-memory JWKS cache (simple implementation)
_jwks_cache: Dict[str, tuple[Any, float]] = {}
JWKS_CACHE_TTL = 600  # 10 minutes


@dataclass
class Principal:
    """Authenticated user principal"""
    subject: str  # OIDC 'sub' claim
    email: Optional[str] = None
    roles: List[str] = None
    raw_claims: Dict[str, Any] = None

    def __post_init__(self):
        if self.roles is None:
            self.roles = []
        if self.raw_claims is None:
            self.raw_claims = {}


class OIDCVerifier:
    """OIDC JWT token verifier with JWKS support"""

    def __init__(self):
        self.settings = get_settings()
        self._jwks_client: Optional[PyJWKClient] = None
        self._ensure_jwks_client()

    def _ensure_jwks_client(self):
        """Ensure JWKS client is initialized"""
        if not self.settings.OIDC_ISSUER_URL:
            logger.warning("OIDC_ISSUER_URL not configured, JWT verification disabled")
            return

        if not self._jwks_client:
            jwks_url = self.settings.oidc_jwks_url
            if not jwks_url:
                raise ValueError("OIDC_JWKS_URL or OIDC_ISSUER_URL must be configured")

            try:
                self._jwks_client = PyJWKClient(
                    jwks_url,
                    cache_keys=True,
                    max_cached_keys=100,
                    cache_ttl=600,  # 10 minutes
                )
                logger.info(f"JWKS client initialized with URL: {jwks_url}")
            except Exception as e:
                logger.error(f"Failed to initialize JWKS client: {e}")
                raise

    def _get_signing_key(self, token: str):
        """Get signing key for token"""
        if not self._jwks_client:
            raise ValueError("JWKS client not initialized")

        try:
            # Decode header without verification to get kid
            unverified = jwt.decode(token, options={"verify_signature": False})
            kid = jwt.get_unverified_header(token).get("kid")
            if not kid:
                raise InvalidTokenError("Token missing 'kid' in header")

            signing_key = self._jwks_client.get_signing_key(kid)
            return signing_key.key
        except Exception as e:
            logger.error(f"Failed to get signing key: {e}")
            raise InvalidTokenError(f"Failed to get signing key: {e}") from e

    def _extract_roles(self, claims: Dict[str, Any]) -> List[str]:
        """Extract roles from JWT claims using configured claim paths"""
        roles = set()
        role_paths = self.settings.oidc_role_claim_paths_list
        audience = self.settings.OIDC_AUDIENCE

        for path in role_paths:
            try:
                # Handle placeholders like {audience}
                resolved_path = path.replace("{audience}", audience) if audience else path

                # Navigate nested structure (e.g., "realm_access.roles")
                parts = resolved_path.split(".")
                value = claims
                for part in parts:
                    if isinstance(value, dict):
                        value = value.get(part)
                    else:
                        value = None
                        break

                if value:
                    if isinstance(value, list):
                        roles.update(value)
                    elif isinstance(value, str):
                        roles.add(value)
            except Exception as e:
                logger.debug(f"Failed to extract roles from path '{path}': {e}")
                continue

        # Map Zitadel roles to internal roles if needed
        # For now, return as-is (expecting USER, ADMIN, COMPLIANCE, OPS, READ_ONLY)
        return sorted(list(roles))

    def verify_token(self, token: str) -> Principal:
        """
        Verify JWT token and return Principal

        Raises:
            InvalidTokenError: If token is invalid
            ExpiredSignatureError: If token is expired
            ValueError: If configuration is missing
        """
        if not self.settings.OIDC_ISSUER_URL:
            raise ValueError("OIDC_ISSUER_URL not configured")

        try:
            # Get signing key
            signing_key = self._get_signing_key(token)

            # Decode and verify token
            algorithms = self.settings.oidc_algorithms_list
            options = {
                "verify_signature": True,
                "verify_exp": True,
                "verify_iat": True,
                "verify_nbf": True,
                "verify_aud": bool(self.settings.OIDC_AUDIENCE),
                "verify_iss": bool(self.settings.OIDC_ISSUER_URL),
            }

            claims = jwt.decode(
                token,
                signing_key,
                algorithms=algorithms,
                audience=self.settings.OIDC_AUDIENCE if self.settings.OIDC_AUDIENCE else None,
                issuer=self.settings.OIDC_ISSUER_URL,
                options=options,
                leeway=self.settings.OIDC_CLOCK_SKEW_SECONDS,
            )

            # Verify required scopes
            required_scopes = self.settings.oidc_required_scopes_list
            if required_scopes:
                token_scopes = claims.get("scope", "").split()
                missing_scopes = set(required_scopes) - set(token_scopes)
                if missing_scopes:
                    raise InvalidTokenError(f"Missing required scopes: {missing_scopes}")

            # Extract principal information
            subject = claims.get("sub")
            if not subject:
                raise InvalidTokenError("Token missing 'sub' claim")

            email = claims.get("email") or claims.get("preferred_username")
            roles = self._extract_roles(claims)

            # If no roles found, default to USER for /api/v1/* endpoints
            # (will be enforced at endpoint level)
            if not roles:
                logger.debug(f"No roles found in token for subject {subject}, defaulting to empty list")

            principal = Principal(
                subject=subject,
                email=email,
                roles=roles,
                raw_claims=claims,
            )

            logger.debug(f"Token verified for subject: {subject}, roles: {roles}")
            return principal

        except ExpiredSignatureError as e:
            logger.warning(f"Token expired: {e}")
            raise
        except InvalidSignatureError as e:
            logger.warning(f"Invalid token signature: {e}")
            raise
        except InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error verifying token: {e}")
            raise InvalidTokenError(f"Token verification failed: {e}") from e


# Global verifier instance (lazy initialization)
_verifier: Optional[OIDCVerifier] = None


def get_verifier() -> OIDCVerifier:
    """Get global OIDC verifier instance"""
    global _verifier
    if _verifier is None:
        _verifier = OIDCVerifier()
    return _verifier


def verify_jwt_token(token: str) -> Principal:
    """
    Verify JWT token and return Principal

    This is the main entry point for token verification.
    """
    verifier = get_verifier()
    return verifier.verify_token(token)

