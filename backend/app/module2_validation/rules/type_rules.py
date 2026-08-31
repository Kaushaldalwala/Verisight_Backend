"""
type_rules.py

Validates types (date parseability, enum membership, country codes) based on field spec.
"""

from typing import Any, Optional
from app.module2_validation.rules.base import BaseValidationRule
from app.module2_validation.schemas.input import DocumentInput
from app.module2_validation.schemas.output import CheckResult, MismatchItem
from app.module2_validation.schemas.common import RuleStatus, Severity
from app.module2_validation.core.normalization import FieldNormalizer


class TypeRules(BaseValidationRule):
    rule_name = "TYPE_VALIDATION"

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
            expected_type = field_spec.get("type")
            raw_val = doc_fields.get(field_name)

            if raw_val is None or str(raw_val).strip() == "":
                continue

            str_val = str(raw_val).strip()

            if expected_type == "date":
                parsed_date = FieldNormalizer.normalize_date(str_val)
                if not parsed_date:
                    checks.append(CheckResult(
                        rule=self.rule_name,
                        status=RuleStatus.FAIL,
                        severity=Severity.MEDIUM,
                        message=f"Field '{field_name}' value '{str_val}' cannot be parsed as a valid date.",
                        field=field_name,
                        ocr_value=str_val
                    ))
                    mismatches.append(MismatchItem(
                        field=field_name,
                        type="INVALID_DATE_TYPE",
                        severity=Severity.MEDIUM,
                        message="Invalid date format",
                        ocr_value=str_val
                    ))

            elif expected_type == "enum":
                allowed = field_spec.get("allowed", [])
                norm_enum = FieldNormalizer.normalize_gender(str_val) if field_name in ("sex", "gender") else str_val.upper()
                allowed_upper = [str(a).upper() for a in allowed]

                if norm_enum not in allowed_upper:
                    checks.append(CheckResult(
                        rule=self.rule_name,
                        status=RuleStatus.FAIL,
                        severity=Severity.MEDIUM,
                        message=f"Field '{field_name}' value '{str_val}' not in allowed values {allowed}.",
                        field=field_name,
                        ocr_value=str_val
                    ))
                    mismatches.append(MismatchItem(
                        field=field_name,
                        type="ENUM_OUT_OF_RANGE",
                        severity=Severity.MEDIUM,
                        message=f"Allowed values: {allowed}",
                        ocr_value=str_val
                    ))

        return checks, mismatches
