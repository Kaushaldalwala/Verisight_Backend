"""
format_rules.py

Validates regex patterns for document identifiers and formatted fields defined in YAML config.
"""

import re
from typing import Any, Optional
from app.module2_validation.rules.base import BaseValidationRule
from app.module2_validation.schemas.input import DocumentInput
from app.module2_validation.schemas.output import CheckResult, MismatchItem
from app.module2_validation.schemas.common import RuleStatus, Severity
from app.module2_validation.core.normalization import FieldNormalizer


class FormatRules(BaseValidationRule):
    rule_name = "FORMAT_VALIDATION"

    def validate(
        self,
        document: DocumentInput,
        config: dict[str, Any],
        context: Optional[dict[str, Any]] = None
    ) -> tuple[list[CheckResult], list[MismatchItem]]:
        checks: list[CheckResult] = []
        mismatches: list[MismatchItem] = []

        fields_config = config.get("fields", {})
        doc_fields = document.fields or {}

        for field_name, field_spec in fields_config.items():
            pattern = field_spec.get("pattern")
            if pattern:
                raw_val = doc_fields.get(field_name)
                if raw_val is not None and str(raw_val).strip() != "":
                    # Normalize for identifier checking
                    norm_val = FieldNormalizer.normalize_identifier(str(raw_val))
                    if field_spec.get("type") == "identifier" and document.document_type == "aadhaar":
                        norm_val = FieldNormalizer.normalize_numeric_identifier(str(raw_val))

                    if not re.match(pattern, norm_val):
                        checks.append(CheckResult(
                            rule=self.rule_name,
                            status=RuleStatus.FAIL,
                            severity=Severity.HIGH,
                            message=f"Field '{field_name}' value '{raw_val}' does not match required format pattern.",
                            field=field_name,
                            ocr_value=raw_val
                        ))
                        mismatches.append(MismatchItem(
                            field=field_name,
                            type="FORMAT_MISMATCH",
                            severity=Severity.HIGH,
                            message=f"Value does not conform to pattern '{pattern}'",
                            ocr_value=raw_val
                        ))
                    else:
                        checks.append(CheckResult(
                            rule=self.rule_name,
                            status=RuleStatus.PASS,
                            severity=Severity.LOW,
                            message=f"Field '{field_name}' matches format pattern.",
                            field=field_name,
                            ocr_value=raw_val
                        ))

        return checks, mismatches
