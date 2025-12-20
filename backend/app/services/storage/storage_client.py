"""
Centralized storage client module for S3/R2 operations
Provides configuration checks and client creation
"""

import boto3
from botocore.exceptions import ClientError, ParamValidationError
from typing import Optional
from app.infrastructure.settings import Settings
from app.services.storage.exceptions import StorageNotConfiguredError


def is_configured(settings: Settings) -> bool:
    """
    Check if storage is properly configured.
    
    Args:
        settings: Application settings
        
    Returns:
        True if storage is configured (bucket + credentials present)
    """
    return settings.storage_enabled


def assert_configured(settings: Settings) -> None:
    """
    Assert that storage is configured, raise StorageNotConfiguredError if not.
    
    Args:
        settings: Application settings
        
    Raises:
        StorageNotConfiguredError: If storage is not configured
    """
    if not is_configured(settings):
        raise StorageNotConfiguredError(
            "Storage is not configured. Set S3_BUCKET, S3_ACCESS_KEY_ID, and S3_SECRET_ACCESS_KEY "
            "(and S3_ENDPOINT_URL/S3_REGION for R2). See docs/STORAGE_R2_SETUP.md for setup instructions."
        )


def create_s3_client(settings: Settings):
    """
    Create a boto3 S3 client with the given settings.
    
    Args:
        settings: Application settings
        
    Returns:
        boto3 S3 client
        
    Raises:
        StorageNotConfiguredError: If storage is not configured
    """
    assert_configured(settings)
    
    config = {
        'aws_access_key_id': settings.S3_ACCESS_KEY_ID,
        'aws_secret_access_key': settings.S3_SECRET_ACCESS_KEY,
        'region_name': settings.S3_REGION or 'us-east-1',  # Default region for AWS
    }
    
    # For R2, we need to set endpoint_url
    if settings.S3_ENDPOINT_URL:
        config['endpoint_url'] = settings.S3_ENDPOINT_URL
    
    try:
        return boto3.client('s3', **config)
    except Exception as e:
        raise StorageNotConfiguredError(
            f"Failed to create S3 client: {str(e)}. Check your S3 configuration."
        )

