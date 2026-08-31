"""
validation_service.py

High-level service class binding Module 1 OCR adapter and Module 2 validation engine.
"""

from typing import Any, Optional
import logging

from app.ocr.adapter import OCROutputAdapter
from app.module2_validation.core.validator import ValidationEngine
from app.module2_validation.schemas.input import DocumentInput
from app.module2_validation.schemas.output import ValidationResult

logger = logging.getLogger(__name__)


class ValidationService:
    """
    Service for validating documents from raw JSON or directly from Module 1 OCR output.
    """

    def __init__(self, validator: Optional[ValidationEngine] = None, db_path: str | None = None):
        self.validator = validator or ValidationEngine(db_path=db_path)

    def validate_direct_input(self, payload: dict[str, Any]) -> ValidationResult:
        doc_input = DocumentInput(
            document_type=payload.get("document_type", "unknown"),
            document_country=payload.get("document_country"),
            ocr_confidence=float(payload.get("ocr_confidence", 100.0)),
            fields=payload.get("fields", {}),
            metadata=payload.get("metadata", {})
        )
        return self.validator.validate_document(doc_input)

    def validate_ocr_output(self, raw_ocr_result: dict[str, Any], doc_type_override: str | None = None) -> ValidationResult:
        adapted = OCROutputAdapter.adapt(raw_ocr_result, doc_type_override)
        doc_input = DocumentInput(
            document_type=adapted["document_type"],
            document_country=adapted["document_country"],
            ocr_confidence=adapted["ocr_confidence"],
            fields=adapted["fields"],
            metadata={"status_raw": adapted["status"], "reason_raw": adapted["reason"]}
        )
        return self.validator.validate_document(doc_input)
