"""
Application settings using pydantic-settings
"""

from functools import lru_cache
from typing import List
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

    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:3001"

    # API Configuration
    API_V1_PREFIX: str = "/api/v1"
    ADMIN_V1_PREFIX: str = "/admin/v1"
    WEBHOOKS_V1_PREFIX: str = "/webhooks/v1"

    @property
    def allowed_origins_list(self) -> List[str]:
        """Parse ALLOWED_ORIGINS into a list"""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]

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

