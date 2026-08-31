"""
required_fields.py

Validates presence of all required fields defined in document type YAML configuration.
"""

from typing import Any, Optional
from app.module2_validation.rules.base import BaseValidationRule
from app.module2_validation.schemas.input import DocumentInput
from app.module2_validation.schemas.output import CheckResult, MismatchItem
from app.module2_validation.schemas.common import RuleStatus, Severity


class RequiredFieldsRule(BaseValidationRule):
    rule_name = "REQUIRED_FIELDS"

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
            if field_spec.get("required", False):
                value = doc_fields.get(field_name)
                is_missing = value is None or str(value).strip() == ""

                if is_missing:
                    checks.append(CheckResult(
                        rule=self.rule_name,
                        status=RuleStatus.FAIL,
                        severity=Severity.HIGH,
                        message=f"Required field '{field_name}' is missing or empty.",
                        field=field_name,
                        ocr_value=None
                    ))
                    mismatches.append(MismatchItem(
                        field=field_name,
                        type="MISSING_REQUIRED_FIELD",
                        severity=Severity.HIGH,
                        message=f"Field '{field_name}' is required by document configuration.",
                        ocr_value=None
                    ))
                else:
                    checks.append(CheckResult(
                        rule=self.rule_name,
                        status=RuleStatus.PASS,
                        severity=Severity.LOW,
                        message=f"Required field '{field_name}' is present.",
                        field=field_name,
                        ocr_value=str(value)
                    ))

        return checks, mismatches
