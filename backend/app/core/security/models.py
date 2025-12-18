"""
Security models - Roles enum
"""

import enum


class Role(str, enum.Enum):
    """RBAC roles"""
    USER = "USER"
    ADMIN = "ADMIN"
    COMPLIANCE = "COMPLIANCE"
    OPS = "OPS"
    READ_ONLY = "READ_ONLY"

