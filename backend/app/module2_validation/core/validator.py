"""
validator.py

Main ValidationEngine orchestrator for VeriSight Module 2.
"""

import time
import logging
from typing import Any, Optional

from app.module2_validation.config.settings import (
    DocumentConfigLoader,
    DATA_PROVIDER_MODE,
)
from app.module2_validation.core.normalization import FieldNormalizer
from app.module2_validation.core.rule_engine import RuleEngine
from app.module2_validation.core.scoring import ScoringEngine
from app.module2_validation.providers.base import DocumentDataProvider
from app.module2_validation.providers.synthetic import SyntheticProvider
from app.module2_validation.providers.government import GovernmentProvider
from app.module2_validation.providers.hybrid import HybridProvider
from app.module2_validation.providers.supabase_provider import SupabaseProvider
from app.module2_validation.schemas.input import DocumentInput
from app.module2_validation.schemas.output import ValidationResult, CheckResult, MismatchItem
from app.module2_validation.schemas.common import (
    ValidationStatus,
    DocumentStatus,
    DataSource,
    RuleStatus,
    Severity,
)

logger = logging.getLogger(__name__)


class ValidationEngine:
    """
    Core document validation engine for Module 2.
    """

    def __init__(self, provider: Optional[DocumentDataProvider] = None, db_path: str | None = None):
        self.db_path = db_path
        if provider is not None:
            self.provider = provider
        else:
            self.provider = SupabaseProvider()

        self.rule_engine = RuleEngine()
        self.scoring_engine = ScoringEngine()

    def validate_document(self, document: DocumentInput) -> ValidationResult:
        start_time = time.monotonic()
        errors: list[str] = []
        warnings: list[str] = []

        try:
            # 1. Load document YAML configuration
            config = DocumentConfigLoader.load_config(document.document_type)

            # 2. Normalize input fields
            norm_fields = FieldNormalizer.normalize_all_fields(document.fields)

            # 3. Locate identifier and query provider
            id_field = config.get("identifier_field")
            identifier = None
            if id_field:
                identifier = norm_fields.get(id_field) or document.fields.get(id_field)

            ref_record = None
            data_source = DataSource.NONE
            source_status = "unconfigured"

            if identifier:
                ref_record, data_source, source_status = self.provider.find_document(document.document_type, str(identifier))

            context = {
                "reference_record": ref_record,
                "data_source": data_source,
                "source_status": source_status
            }

            # 4. Run rule engine
            checks, mismatches = self.rule_engine.execute(document, config, context)

            # 5. Calculate validation score & recommendation
            score, recommendation = self.scoring_engine.calculate_score(checks, document.ocr_confidence)

            # 6. Determine document status from reference record
            doc_status = DocumentStatus.NOT_FOUND
            if ref_record:
                status_raw = str(ref_record.get("status", "ACTIVE")).upper()
                try:
                    doc_status = DocumentStatus(status_raw)
                except ValueError:
                    doc_status = DocumentStatus.ACTIVE

            db_match = ref_record is not None

            # Collect warnings
            for c in checks:
                if c.status == RuleStatus.WARNING:
                    warnings.append(c.message)

            elapsed_ms = int((time.monotonic() - start_time) * 1000)

            return ValidationResult(
                request_id=document.request_id,
                document_type=document.document_type,
                validation_status=recommendation,
                validation_score=score,
                database_match=db_match,
                data_source=data_source,
                source_status=source_status,
                document_status=doc_status,
                checks=checks,
                mismatches=mismatches,
                warnings=warnings,
                errors=errors,
                recommendation=recommendation,
                processing_time_ms=elapsed_ms,
                normalized_fields=norm_fields
            )

        except Exception as exc:
            logger.error("Unhandled exception during document validation: %s", exc, exc_info=True)
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            return ValidationResult(
                request_id=document.request_id,
                document_type=document.document_type,
                validation_status=ValidationStatus.ERROR,
                validation_score=0.0,
                database_match=False,
                data_source=DataSource.NONE,
                source_status="error",
                document_status=DocumentStatus.UNKNOWN,
                checks=[
                    CheckResult(
                        rule="VALIDATION_ENGINE",
                        status=RuleStatus.FAIL,
                        severity=Severity.CRITICAL,
                        message=f"Validation failed due to internal error: {exc}"
                    )
                ],
                mismatches=[],
                warnings=[],
                errors=[str(exc)],
                recommendation=ValidationStatus.FAIL,
                processing_time_ms=elapsed_ms,
                normalized_fields={}
            )
