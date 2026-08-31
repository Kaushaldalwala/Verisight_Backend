"""
output.py

Output schemas for Module 2 Document Validation.
"""

from typing import Any, Optional
from pydantic import BaseModel, Field

from app.module2_validation.schemas.common import (
    ValidationStatus,
    RuleStatus,
    Severity,
    DocumentStatus,
    DataSource,
)


class CheckResult(BaseModel):
    """Result of a single validation check."""
    rule: str
    status: RuleStatus
    severity: Severity = Severity.LOW
    message: str = ""
    field: Optional[str] = None
    ocr_value: Optional[Any] = None
    reference_value: Optional[Any] = None


class MismatchItem(BaseModel):
    """Detailed field mismatch info."""
    field: str
    type: str
    severity: Severity
    message: str
    ocr_value: Optional[Any] = None
    reference_value: Optional[Any] = None


class ValidationResult(BaseModel):
    """
    Standardized, professional validation output structure for VeriSight Module 2.
    """
    request_id: str
    document_type: str
    validation_status: ValidationStatus
    validation_score: float = Field(..., ge=0.0, le=100.0)
    database_match: bool = False
    data_source: DataSource = DataSource.NONE
    source_status: str = "demonstration_only"
    document_status: DocumentStatus = DocumentStatus.UNKNOWN
    checks: list[CheckResult] = Field(default_factory=list)
    mismatches: list[MismatchItem] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    recommendation: ValidationStatus
    processing_time_ms: int = 0
    normalized_fields: dict[str, Any] = Field(default_factory=dict)
