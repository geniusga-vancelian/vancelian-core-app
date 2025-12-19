"""
Application settings using pydantic-settings
"""

from functools import lru_cache
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Environment (local, staging, prod)
    ENV: str = "local"
    LOG_LEVEL: str = "INFO"
    
    # Development mode (enables DEV-only endpoints)
    # ⚠️ SECURITY: Defaults to False - must be explicitly enabled for development
    # When DEV_MODE=False:
    #   - All /dev/v1/* endpoints return HTTP 404 (not found)
    #   - DEV routers are not loaded/registered
    #   - Bootstrap endpoints are unreachable
    # Only set DEV_MODE=True in development/staging environments, NEVER in production
    DEV_MODE: bool = False

    # Database
    DATABASE_URL: str = "postgresql://vancelian:vancelian_password@postgres:5432/vancelian_core"

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"

    # Security
    SECRET_KEY: str = "your-secret-key-here-change-in-production-min-32-chars"
    
    # Webhook Security - ZAND Bank
    ZAND_WEBHOOK_SECRET: str = ""  # HMAC secret for ZAND webhook signature verification
    ZAND_WEBHOOK_TOLERANCE_SECONDS: int = 300  # Timestamp tolerance for replay protection (default: 5 minutes)
    
    # Rate Limiting
    RL_WEBHOOK_PER_MIN: int = 120  # Rate limit for /webhooks/v1/* endpoints (requests per minute)
    RL_ADMIN_PER_MIN: int = 60  # Rate limit for /admin/v1/* endpoints (requests per minute)
    RL_API_PER_MIN: int = 120  # Rate limit for /api/v1/* endpoints (requests per minute)
    
    # Security Headers
    ENABLE_HSTS: bool = False  # Enable HSTS header (set to True in production)
    
    # Observability / Metrics
    METRICS_PUBLIC: bool = False  # Make /metrics endpoint public (default: protected)
    METRICS_TOKEN: str = ""  # Static token for /metrics access (if METRICS_PUBLIC=false)

    # OIDC / JWT Authentication (Zitadel-compatible)
    OIDC_ISSUER_URL: str = ""  # OIDC issuer URL (e.g., https://auth.zitadel.cloud)
    OIDC_AUDIENCE: str = ""  # Expected audience (client ID)
    OIDC_JWKS_URL: str = ""  # Optional: explicit JWKS URL (if absent, derived from issuer/.well-known/jwks.json)
    OIDC_ALGORITHMS: str = "RS256"  # Allowed JWT algorithms (comma-separated, default: RS256)
    OIDC_REQUIRED_SCOPES: str = ""  # Optional: required scopes (comma-separated)
    OIDC_CLOCK_SKEW_SECONDS: int = 60  # Clock skew tolerance for token validation (default: 60 seconds)
    OIDC_ROLE_CLAIM_PATHS: str = "realm_access.roles,resource_access.{audience}.roles,roles"  # Comma-separated paths to extract roles from JWT claims
    
    # JWT Symmetric Key (for HS256 development mode)
    JWT_SECRET: str = ""  # Secret key for HS256 JWT signing/verification (dev only)
    JWT_ALGORITHM: str = "HS256"  # JWT algorithm when using symmetric key (default: HS256)

    # CORS Configuration
    CORS_ENABLED: bool = True  # Enable CORS middleware (dev default)
    
    # CORS settings - can be strings (comma-separated) or lists
    # Lists are preferred, but strings from env vars are auto-parsed
    CORS_ALLOW_ORIGINS: Union[str, List[str]] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ]
    CORS_ALLOW_METHODS: Union[str, List[str]] = ["*"]  # Allow all methods for dev flexibility
    CORS_ALLOW_HEADERS: Union[str, List[str]] = [
        "Authorization",
        "Content-Type",
        "Idempotency-Key",
        "X-Request-Id",
        "Accept",
        "Origin",
        # Webhook-related headers (required for DEV frontend simulator)
        "X-Webhook-Signature",
        "X-Webhook-Timestamp",
        "X-Zand-Signature",
        "X-Zand-Timestamp",
    ]
    CORS_ALLOW_CREDENTIALS: bool = True  # Allow credentials (cookies, Authorization headers) for frontend-admin uploads
    
    # Legacy: ALLOWED_ORIGINS (for backward compatibility)
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001"

    # API Configuration
    API_V1_PREFIX: str = "/api/v1"
    ADMIN_V1_PREFIX: str = "/admin/v1"
    WEBHOOKS_V1_PREFIX: str = "/webhooks/v1"
    
    # S3/R2 Storage Configuration
    STORAGE_PROVIDER: str = "s3"  # "s3" for AWS S3 or Cloudflare R2
    S3_ENDPOINT_URL: str = ""  # Required for R2 (e.g., https://<account-id>.r2.cloudflarestorage.com), empty for AWS
    S3_REGION: str = "auto"  # "auto" for R2, or AWS region like "eu-west-1"
    S3_ACCESS_KEY_ID: str = ""
    S3_SECRET_ACCESS_KEY: str = ""
    S3_BUCKET: str = ""
    S3_PUBLIC_BASE_URL: str = ""  # Optional: CDN/public base URL (e.g., https://cdn.example.com)
    S3_PRESIGN_EXPIRES_SECONDS: int = 900  # Presigned URL expiration (default: 15 minutes)
    S3_KEY_PREFIX: str = "offers"  # Prefix for all object keys (e.g., "offers/{offer_id}/...")
    
    # Upload size limits (in bytes)
    S3_MAX_DOCUMENT_SIZE: int = 50 * 1024 * 1024  # 50MB default
    S3_MAX_VIDEO_SIZE: int = 200 * 1024 * 1024  # 200MB default
    S3_MAX_IMAGE_SIZE: int = 10 * 1024 * 1024  # 10MB default

    @field_validator('CORS_ALLOW_ORIGINS', mode='before')
    @classmethod
    def parse_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        """Parse CORS_ALLOW_ORIGINS from string (comma-separated) or list"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v if isinstance(v, list) else []
    
    @field_validator('CORS_ALLOW_METHODS', mode='before')
    @classmethod
    def parse_cors_methods(cls, v: Union[str, List[str]]) -> List[str]:
        """Parse CORS_ALLOW_METHODS from string (comma-separated) or list"""
        if isinstance(v, str):
            return [method.strip() for method in v.split(",") if method.strip()]
        return v if isinstance(v, list) else []
    
    @field_validator('CORS_ALLOW_HEADERS', mode='before')
    @classmethod
    def parse_cors_headers(cls, v: Union[str, List[str]]) -> List[str]:
        """Parse CORS_ALLOW_HEADERS from string (comma-separated) or list"""
        if isinstance(v, str):
            return [header.strip() for header in v.split(",") if header.strip()]
        return v if isinstance(v, list) else []

    @property
    def cors_allow_origins_list(self) -> List[str]:
        """Get CORS_ALLOW_ORIGINS as a list (already parsed by validator)"""
        return self.CORS_ALLOW_ORIGINS if isinstance(self.CORS_ALLOW_ORIGINS, list) else []
    
    @property
    def cors_allow_methods_list(self) -> List[str]:
        """Get CORS_ALLOW_METHODS as a list (already parsed by validator)"""
        return self.CORS_ALLOW_METHODS if isinstance(self.CORS_ALLOW_METHODS, list) else []
    
    @property
    def cors_allow_headers_list(self) -> List[str]:
        """Get CORS_ALLOW_HEADERS as a list (already parsed by validator)"""
        return self.CORS_ALLOW_HEADERS if isinstance(self.CORS_ALLOW_HEADERS, list) else []
    
    @property
    def allowed_origins_list(self) -> List[str]:
        """Parse ALLOWED_ORIGINS into a list (backward compatibility)"""
        return self.cors_allow_origins_list

    @property
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.ENV.lower() == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.ENV.lower() in ["production", "prod"]
    
    @property
    def is_test(self) -> bool:
        """Check if running in test environment"""
        return self.ENV.lower() == "test"

    @property
    def debug(self) -> bool:
        """Debug mode: enabled if not production"""
        return self.ENV.lower() != "prod"

    @property
    def oidc_algorithms_list(self) -> List[str]:
        """Parse OIDC_ALGORITHMS into a list"""
        return [alg.strip() for alg in self.OIDC_ALGORITHMS.split(",") if alg.strip()]

    @property
    def oidc_required_scopes_list(self) -> List[str]:
        """Parse OIDC_REQUIRED_SCOPES into a list"""
        if not self.OIDC_REQUIRED_SCOPES:
            return []
        return [scope.strip() for scope in self.OIDC_REQUIRED_SCOPES.split(",") if scope.strip()]

    @property
    def oidc_role_claim_paths_list(self) -> List[str]:
        """Parse OIDC_ROLE_CLAIM_PATHS into a list"""
        return [path.strip() for path in self.OIDC_ROLE_CLAIM_PATHS.split(",") if path.strip()]

    @property
    def oidc_jwks_url(self) -> str:
        """Get JWKS URL (explicit or derived from issuer)"""
        if self.OIDC_JWKS_URL:
            return self.OIDC_JWKS_URL
        if self.OIDC_ISSUER_URL:
            return f"{self.OIDC_ISSUER_URL.rstrip('/')}/.well-known/jwks.json"
        return ""


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()

