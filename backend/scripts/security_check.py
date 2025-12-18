#!/usr/bin/env python3
"""
Security baseline checks for CI/CD.

Verifies:
- Required environment variables exist
- Security settings are properly configured
- No default/weak secrets in non-test environments
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.infrastructure.settings import get_settings


def check_required_env_vars():
    """Check that required environment variables are set"""
    settings = get_settings()
    
    required_vars = {
        'DATABASE_URL': settings.DATABASE_URL,
        'REDIS_URL': settings.REDIS_URL,
        'SECRET_KEY': settings.SECRET_KEY,
    }
    
    missing = []
    for var, value in required_vars.items():
        if not value:
            missing.append(var)
    
    if missing:
        print(f"❌ Missing required environment variables: {', '.join(missing)}")
        return False
    
    print("✅ All required environment variables are set")
    return True


def check_secrets(env: str):
    """Check that secrets are properly configured"""
    settings = get_settings()
    
    issues = []
    
    # Check SECRET_KEY
    if settings.SECRET_KEY == "your-secret-key-here-change-in-production-min-32-chars":
        if env.lower() not in ["test", "development", "local"]:
            issues.append("SECRET_KEY is using default value in non-dev environment")
    
    if len(settings.SECRET_KEY) < 32:
        issues.append(f"SECRET_KEY is too short (min 32 chars, got {len(settings.SECRET_KEY)})")
    
    # Check ZAND_WEBHOOK_SECRET (required in production)
    if env.lower() not in ["test", "development", "local"]:
        if not settings.ZAND_WEBHOOK_SECRET:
            issues.append("ZAND_WEBHOOK_SECRET must be set in non-dev environments")
        elif settings.ZAND_WEBHOOK_SECRET == "your-zand-webhook-secret-here-change-in-production":
            issues.append("ZAND_WEBHOOK_SECRET is using default value in non-dev environment")
    
    if issues:
        for issue in issues:
            print(f"❌ {issue}")
        return False
    
    print("✅ Secrets are properly configured")
    return True


def check_rate_limit_config():
    """Check that rate limit configuration is valid"""
    settings = get_settings()
    
    issues = []
    
    if settings.RL_WEBHOOK_PER_MIN <= 0:
        issues.append("RL_WEBHOOK_PER_MIN must be > 0")
    
    if settings.RL_ADMIN_PER_MIN <= 0:
        issues.append("RL_ADMIN_PER_MIN must be > 0")
    
    if settings.RL_API_PER_MIN <= 0:
        issues.append("RL_API_PER_MIN must be > 0")
    
    if issues:
        for issue in issues:
            print(f"❌ {issue}")
        return False
    
    print(f"✅ Rate limit configuration valid:")
    print(f"   - Webhooks: {settings.RL_WEBHOOK_PER_MIN} req/min")
    print(f"   - Admin: {settings.RL_ADMIN_PER_MIN} req/min")
    print(f"   - API: {settings.RL_API_PER_MIN} req/min")
    return True


def check_security_headers():
    """Check security headers configuration"""
    settings = get_settings()
    
    # HSTS should be enabled in production
    if settings.is_production and not settings.ENABLE_HSTS:
        print("⚠️  HSTS is disabled in production (consider enabling)")
    
    print("✅ Security headers configuration checked")
    return True


def main():
    """Run all security checks"""
    settings = get_settings()
    env = settings.ENV
    
    print(f"Running security checks for environment: {env}")
    print("-" * 50)
    
    success = True
    success &= check_required_env_vars()
    success &= check_secrets(env)
    success &= check_rate_limit_config()
    success &= check_security_headers()
    
    print("-" * 50)
    if success:
        print("✅ All security baseline checks passed")
        return 0
    else:
        print("❌ Security baseline checks failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())


