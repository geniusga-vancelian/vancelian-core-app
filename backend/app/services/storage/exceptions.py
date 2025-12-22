"""
Storage-related exceptions
"""


class StorageNotConfiguredError(Exception):
    """Raised when storage (S3/R2) is not properly configured"""
    
    def __init__(self, message: str = "Storage is not configured"):
        self.code = "STORAGE_NOT_CONFIGURED"
        self.message = message
        super().__init__(self.message)

