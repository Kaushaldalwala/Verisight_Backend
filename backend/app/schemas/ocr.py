from typing import Any, Optional
from pydantic import BaseModel
from app.module2_validation.schemas.output import ValidationResult


class OCRResponse(BaseModel):
    """
    Unified OCR response schema returned by /ocr/* endpoints.
    Includes Module 1 extraction results and integrated Module 2 validation results.
    """

    document_type:  str
    status:         str
    ocr_confidence: float = 0.0
    reason:         str = ""
    fields:         dict[str, Any] = {}
    scan_log_id:    Optional[str] = None
    validation:     Optional[ValidationResult] = None
