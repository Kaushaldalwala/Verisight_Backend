"""
common.py

Enums and shared types for Module 2 Document Validation.
"""

from enum import Enum


class ValidationStatus(str, Enum):
    PASS = "PASS"
    MANUAL_REVIEW = "MANUAL_REVIEW"
    FAIL = "FAIL"
    ERROR = "ERROR"


class RuleStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    WARNING = "WARNING"
    SKIPPED = "SKIPPED"


class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class DocumentStatus(str, Enum):
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"
    LOST = "LOST"
    BLACKLISTED = "BLACKLISTED"
    SUSPENDED = "SUSPENDED"
    NOT_FOUND = "NOT_FOUND"
    UNKNOWN = "UNKNOWN"


class DataSource(str, Enum):
    SYNTHETIC_DATABASE = "synthetic_database"
    GOVERNMENT_API = "government_api"
    HYBRID = "hybrid"
    LOCAL_CACHE = "local_cache"
    NONE = "none"
