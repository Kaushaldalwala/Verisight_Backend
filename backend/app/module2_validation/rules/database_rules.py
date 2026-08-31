"""
database_rules.py

Database lookup and reference field comparison rules.
"""

from typing import Any, Optional
from app.module2_validation.rules.base import BaseValidationRule
from app.module2_validation.schemas.input import DocumentInput
from app.module2_validation.schemas.output import CheckResult, MismatchItem
from app.module2_validation.schemas.common import RuleStatus, Severity
from app.module2_validation.core.normalization import FieldNormalizer


class DatabaseRules(BaseValidationRule):
    rule_name = "DATABASE_VALIDATION"

    def validate(
        self,
        document: DocumentInput,
        config: dict[str, Any],
        context: Optional[dict[str, Any]] = None
    ) -> tuple[list[CheckResult], list[MismatchItem]]:
        checks: list[CheckResult] = []
        mismatches: list[MismatchItem] = []

        if not context or not context.get("reference_record"):
            checks.append(CheckResult(
                rule="DATABASE_LOOKUP",
                status=RuleStatus.FAIL,
                severity=Severity.HIGH,
                message="No record found in reference database matching identifier.",
                field=config.get("identifier_field")
            ))
            mismatches.append(MismatchItem(
                field=config.get("identifier_field", "identifier"),
                type="DATABASE_NOT_FOUND",
                severity=Severity.HIGH,
                message="Identifier not found in registry database"
            ))
            return checks, mismatches

        record = context["reference_record"]
        doc_fields = document.fields or {}

        # Perform field comparisons
        for field, ref_val in record.items():
            if field in ("id", "status", "created_at", "updated_at", "document_type"):
                continue

            ocr_val = doc_fields.get(field)
            if ocr_val is None or ref_val is None:
                continue

            if field == "name":
                match, ratio = FieldNormalizer.fuzzy_match_names(str(ocr_val), str(ref_val))
                if not match:
                    checks.append(CheckResult(
                        rule="DATABASE_FIELD_MATCH",
                        status=RuleStatus.FAIL,
                        severity=Severity.HIGH,
                        message=f"Name mismatch in DB: OCR '{ocr_val}' vs DB '{ref_val}' (Similarity: {ratio}%)",
                        field="name",
                        ocr_value=ocr_val,
                        reference_value=ref_val
                    ))
                    mismatches.append(MismatchItem(
                        field="name",
                        type="DATABASE_MISMATCH",
                        severity=Severity.HIGH,
                        message=f"Name mismatch (Similarity: {ratio}%)",
                        ocr_value=ocr_val,
                        reference_value=ref_val
                    ))
                else:
                    checks.append(CheckResult(
                        rule="DATABASE_FIELD_MATCH",
                        status=RuleStatus.PASS,
                        severity=Severity.LOW,
                        message=f"Name match in DB (Similarity: {ratio}%).",
                        field="name",
                        ocr_value=ocr_val,
                        reference_value=ref_val
                    ))

            elif "date" in field:
                norm_ocr = FieldNormalizer.normalize_date(str(ocr_val))
                norm_ref = FieldNormalizer.normalize_date(str(ref_val))
                if norm_ocr and norm_ref and norm_ocr != norm_ref:
                    checks.append(CheckResult(
                        rule="DATABASE_FIELD_MATCH",
                        status=RuleStatus.FAIL,
                        severity=Severity.HIGH,
                        message=f"Field '{field}' mismatch in DB: OCR '{norm_ocr}' vs DB '{norm_ref}'",
                        field=field,
                        ocr_value=norm_ocr,
                        reference_value=norm_ref
                    ))
                    mismatches.append(MismatchItem(
                        field=field,
                        type="DATABASE_MISMATCH",
                        severity=Severity.HIGH,
                        message=f"Date mismatch",
                        ocr_value=norm_ocr,
                        reference_value=norm_ref
                    ))

        return checks, mismatches
