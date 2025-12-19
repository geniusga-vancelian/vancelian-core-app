"""
S3/R2 Storage Service - Handles presigned URLs and object operations
"""

import boto3
from botocore.exceptions import ClientError
from typing import Optional
from uuid import UUID
from datetime import timedelta
from app.infrastructure.settings import get_settings


class S3Service:
    """Service for S3/R2 operations using boto3"""
    
    def __init__(self):
        self.settings = get_settings()
        self._client = None
    
    @property
    def client(self):
        """Lazy initialization of boto3 client"""
        if self._client is None:
            config = {
                'aws_access_key_id': self.settings.S3_ACCESS_KEY_ID,
                'aws_secret_access_key': self.settings.S3_SECRET_ACCESS_KEY,
                'region_name': self.settings.S3_REGION,
            }
            
            # For R2, we need to set endpoint_url
            if self.settings.S3_ENDPOINT_URL:
                config['endpoint_url'] = self.settings.S3_ENDPOINT_URL
            
            self._client = boto3.client('s3', **config)
        
        return self._client
    
    def generate_presigned_put_url(
        self,
        key: str,
        mime_type: str,
        expires_in: Optional[int] = None,
    ) -> str:
        """
        Generate a presigned PUT URL for uploading a file
        
        Args:
            key: S3 object key (full path)
            mime_type: Content-Type for the upload
            expires_in: Expiration time in seconds (defaults to S3_PRESIGN_EXPIRES_SECONDS)
        
        Returns:
            Presigned PUT URL
        
        Raises:
            ValueError: If S3 is not configured or if boto3 fails
        """
        # Validate S3 configuration
        if not self.settings.S3_BUCKET:
            raise ValueError(
                "S3 storage is not configured. Please set S3_BUCKET environment variable. "
                "See docs/STORAGE_R2_SETUP.md for setup instructions."
            )
        
        expires_in = expires_in or self.settings.S3_PRESIGN_EXPIRES_SECONDS
        
        try:
            url = self.client.generate_presigned_url(
                'put_object',
                Params={
                    'Bucket': self.settings.S3_BUCKET,
                    'Key': key,
                    'ContentType': mime_type,
                },
                ExpiresIn=expires_in,
            )
            return url
        except ClientError as e:
            raise ValueError(f"Failed to generate presigned PUT URL: {str(e)}")
        except Exception as e:
            # Catch ParamValidationError and other boto3 errors
            raise ValueError(f"S3 configuration error: {str(e)}")
    
    def generate_presigned_get_url(
        self,
        key: str,
        expires_in: Optional[int] = None,
    ) -> str:
        """
        Generate a presigned GET URL for downloading a file
        
        Args:
            key: S3 object key (full path)
            expires_in: Expiration time in seconds (defaults to S3_PRESIGN_EXPIRES_SECONDS)
        
        Returns:
            Presigned GET URL
        
        Raises:
            ValueError: If S3 is not configured or if boto3 fails
        """
        # Validate S3 configuration
        if not self.settings.S3_BUCKET:
            raise ValueError(
                "S3 storage is not configured. Please set S3_BUCKET environment variable. "
                "See docs/STORAGE_R2_SETUP.md for setup instructions."
            )
        
        expires_in = expires_in or self.settings.S3_PRESIGN_EXPIRES_SECONDS
        
        try:
            url = self.client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.settings.S3_BUCKET,
                    'Key': key,
                },
                ExpiresIn=expires_in,
            )
            return url
        except ClientError as e:
            raise ValueError(f"Failed to generate presigned GET URL: {str(e)}")
        except Exception as e:
            # Catch ParamValidationError and other boto3 errors
            raise ValueError(f"S3 configuration error: {str(e)}")
    
    def build_object_key(
        self,
        offer_id: UUID,
        file_name: str,
        upload_type: str,  # "media" or "document"
    ) -> str:
        """
        Build S3 object key with prefix and offer_id
        
        Args:
            offer_id: Offer UUID
            upload_type: "media" or "document"
            file_name: Original file name (will be sanitized)
        
        Returns:
            Full S3 object key (e.g., "offers/{offer_id}/media/image.jpg")
        """
        import os
        import re
        
        # Sanitize file name (remove path separators, keep only safe chars)
        safe_name = re.sub(r'[^a-zA-Z0-9._-]', '_', os.path.basename(file_name))
        
        # Build key with prefix
        key = f"{self.settings.S3_KEY_PREFIX}/{str(offer_id)}/{upload_type}/{safe_name}"
        
        return key
    
    def validate_mime_type(self, mime_type: str, upload_type: str, media_type: Optional[str] = None) -> bool:
        """
        Validate MIME type based on upload type and media type
        
        Args:
            mime_type: MIME type to validate
            upload_type: "media" or "document"
            media_type: "IMAGE" or "VIDEO" (required if upload_type="media")
        
        Returns:
            True if valid, raises ValueError if invalid
        """
        if upload_type == "media":
            if not media_type:
                raise ValueError("media_type is required for media uploads")
            
            if media_type == "IMAGE":
                if not mime_type.startswith("image/"):
                    raise ValueError(f"Invalid MIME type for image: {mime_type}. Expected image/*")
            elif media_type == "VIDEO":
                if not mime_type.startswith("video/"):
                    raise ValueError(f"Invalid MIME type for video: {mime_type}. Expected video/*")
            else:
                raise ValueError(f"Invalid media_type: {media_type}. Expected IMAGE or VIDEO")
        
        elif upload_type == "document":
            allowed_doc_types = [
                "application/pdf",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # .xlsx
                "application/vnd.ms-excel",  # .xls
                "application/msword",  # .doc
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
            ]
            if mime_type not in allowed_doc_types:
                raise ValueError(
                    f"Invalid MIME type for document: {mime_type}. "
                    f"Allowed: {', '.join(allowed_doc_types)}"
                )
        else:
            raise ValueError(f"Invalid upload_type: {upload_type}. Expected 'media' or 'document'")
        
        return True
    
    def validate_size(self, size_bytes: int, upload_type: str, media_type: Optional[str] = None) -> bool:
        """
        Validate file size based on upload type and media type
        
        Args:
            size_bytes: File size in bytes
            upload_type: "media" or "document"
            media_type: "IMAGE" or "VIDEO" (required if upload_type="media")
        
        Returns:
            True if valid, raises ValueError if invalid
        """
        if upload_type == "media":
            if not media_type:
                raise ValueError("media_type is required for media uploads")
            
            if media_type == "IMAGE":
                max_size = self.settings.S3_MAX_IMAGE_SIZE
            elif media_type == "VIDEO":
                max_size = self.settings.S3_MAX_VIDEO_SIZE
            else:
                raise ValueError(f"Invalid media_type: {media_type}")
        elif upload_type == "document":
            max_size = self.settings.S3_MAX_DOCUMENT_SIZE
        else:
            raise ValueError(f"Invalid upload_type: {upload_type}")
        
        if size_bytes <= 0:
            raise ValueError("File size must be greater than 0")
        
        if size_bytes > max_size:
            raise ValueError(
                f"File size {size_bytes} bytes exceeds maximum allowed size {max_size} bytes "
                f"({max_size / (1024 * 1024):.1f}MB)"
            )
        
        return True


# Singleton instance
_s3_service: Optional[S3Service] = None


def get_s3_service() -> S3Service:
    """Get singleton S3Service instance"""
    global _s3_service
    if _s3_service is None:
        _s3_service = S3Service()
    return _s3_service

