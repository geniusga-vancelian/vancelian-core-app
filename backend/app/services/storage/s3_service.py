"""
S3/R2 Storage Service - Handles presigned URLs and object operations
"""

import boto3
from botocore.exceptions import ClientError
from typing import Optional
from uuid import UUID
from datetime import timedelta
from app.infrastructure.settings import get_settings
from app.services.storage.storage_client import assert_configured, create_s3_client
from app.services.storage.exceptions import StorageNotConfiguredError


class S3Service:
    """Service for S3/R2 operations using boto3"""
    
    def __init__(self):
        self.settings = get_settings()
        self._client = None
    
    @property
    def client(self):
        """Lazy initialization of boto3 client"""
        if self._client is None:
            # Use centralized client creation with proper error handling
            self._client = create_s3_client(self.settings)
        
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
            StorageNotConfiguredError: If S3 is not configured
            ValueError: If boto3 fails
        """
        # Validate S3 configuration using centralized check
        assert_configured(self.settings)
        
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
            raise ValueError(f"S3 operation error: {str(e)}")
    
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
            StorageNotConfiguredError: If S3 is not configured
            ValueError: If boto3 fails
        """
        # Validate S3 configuration using centralized check
        assert_configured(self.settings)
        
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
            raise ValueError(f"S3 operation error: {str(e)}")
    
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
    
    def build_article_object_key(
        self,
        article_id: UUID,
        file_name: str,
        upload_type: str,  # "image", "video", or "document"
    ) -> str:
        """
        Build S3 object key for article media with prefix and article_id
        
        Args:
            article_id: Article UUID
            upload_type: "image", "video", or "document"
            file_name: Original file name (will be sanitized)
        
        Returns:
            Full S3 object key (e.g., "articles/{article_id}/{upload_type}/{uuid}.{ext}")
        """
        import os
        import re
        import uuid as uuid_lib
        
        # Sanitize file name (remove path separators, keep only safe chars)
        base_name = os.path.basename(file_name)
        name_without_ext, ext = os.path.splitext(base_name)
        safe_name = re.sub(r'[^a-zA-Z0-9._-]', '_', name_without_ext)
        
        # Use UUID for uniqueness (similar to how uploads work)
        unique_id = str(uuid_lib.uuid4())[:8]
        safe_name_with_ext = f"{safe_name}_{unique_id}{ext}"
        
        # Use ARTICLES_KEY_PREFIX if set, otherwise default to "articles"
        prefix = getattr(self.settings, 'ARTICLES_KEY_PREFIX', 'articles')
        
        # Build key with prefix
        key = f"{prefix}/{str(article_id)}/{upload_type}/{safe_name_with_ext}"
        
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

