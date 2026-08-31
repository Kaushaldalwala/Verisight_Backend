"""
consistency_rules.py

Cross-field consistency validation rules.
"""

from typing import Any, Optional
from app.module2_validation.rules.base import BaseValidationRule
from app.module2_validation.schemas.input import DocumentInput
from app.module2_validation.schemas.output import CheckResult, MismatchItem
from app.module2_validation.schemas.common import RuleStatus, Severity
from app.module2_validation.core.normalization import FieldNormalizer


class ConsistencyRules(BaseValidationRule):
    rule_name = "CROSS_FIELD_CONSISTENCY"

    def validate(
        self,
        document: DocumentInput,
        config: dict[str, Any],
        context: Optional[dict[str, Any]] = None
    ) -> tuple[list[CheckResult], list[MismatchItem]]:
        checks: list[CheckResult] = []
        mismatches: list[MismatchItem] = []

        rules = config.get("cross_field_rules", [])
        doc_fields = document.fields or {}

        for rule_item in rules:
            rule_type = rule_item.get("rule")

            if rule_type == "date_before":
                field_a = rule_item.get("field_a")
                field_b = rule_item.get("field_b")
                val_a = FieldNormalizer.normalize_date(doc_fields.get(field_a))
                val_b = FieldNormalizer.normalize_date(doc_fields.get(field_b))

                if val_a and val_b and val_a > val_b:
                    checks.append(CheckResult(
                        rule=self.rule_name,
                        status=RuleStatus.FAIL,
                        severity=Severity.HIGH,
                        message=f"Cross-field failure: '{field_a}' ({val_a}) is after '{field_b}' ({val_b}).",
                        field=field_a,
                        ocr_value=val_a,
                        reference_value=val_b
                    ))
                    mismatches.append(MismatchItem(
                        field=field_a,
                        type="CROSS_FIELD_MISMATCH",
                        severity=Severity.HIGH,
                        message=f"'{field_a}' must be before '{field_b}'",
                        ocr_value=val_a,
                        reference_value=val_b
                    ))

        return checks, mismatches
