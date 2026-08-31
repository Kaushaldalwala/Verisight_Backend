"""
date_rules.py

Validates date relationships (DOB not in future, issue date not in future, expiry after issue).
Uses current runtime date — NOT hardcoded static dates.
"""

from datetime import datetime, date
from typing import Any, Optional
from app.module2_validation.rules.base import BaseValidationRule
from app.module2_validation.schemas.input import DocumentInput
from app.module2_validation.schemas.output import CheckResult, MismatchItem
from app.module2_validation.schemas.common import RuleStatus, Severity
from app.module2_validation.core.normalization import FieldNormalizer


class DateRules(BaseValidationRule):
    rule_name = "DATE_VALIDATION"

    def validate(
        self,
        document: DocumentInput,
        config: dict[str, Any],
        context: Optional[dict[str, Any]] = None
    ) -> tuple[list[CheckResult], list[MismatchItem]]:
        checks: list[CheckResult] = []
        mismatches: list[MismatchItem] = []

        doc_fields = document.fields or {}
        today = date.today()

        dob_str = FieldNormalizer.normalize_date(doc_fields.get("date_of_birth"))
        issue_str = FieldNormalizer.normalize_date(doc_fields.get("date_of_issue"))
        expiry_str = FieldNormalizer.normalize_date(doc_fields.get("date_of_expiry"))

        # DOB check
        if dob_str:
            dob = datetime.strptime(dob_str, "%Y-%m-%d").date()
            if dob > today:
                checks.append(CheckResult(
                    rule=self.rule_name,
                    status=RuleStatus.FAIL,
                    severity=Severity.HIGH,
                    message=f"Date of birth '{dob_str}' is in the future relative to runtime date {today}.",
                    field="date_of_birth",
                    ocr_value=dob_str
                ))
                mismatches.append(MismatchItem(
                    field="date_of_birth",
                    type="FUTURE_DOB",
                    severity=Severity.HIGH,
                    message="Date of birth cannot be in the future",
                    ocr_value=dob_str
                ))

        # Issue date check
        if issue_str:
            issue = datetime.strptime(issue_str, "%Y-%m-%d").date()
            if issue > today:
                checks.append(CheckResult(
                    rule=self.rule_name,
                    status=RuleStatus.FAIL,
                    severity=Severity.MEDIUM,
                    message=f"Date of issue '{issue_str}' is in the future relative to runtime date {today}.",
                    field="date_of_issue",
                    ocr_value=issue_str
                ))

        # Expiry vs Issue check
        if issue_str and expiry_str:
            issue = datetime.strptime(issue_str, "%Y-%m-%d").date()
            expiry = datetime.strptime(expiry_str, "%Y-%m-%d").date()
            if expiry <= issue:
                checks.append(CheckResult(
                    rule=self.rule_name,
                    status=RuleStatus.FAIL,
                    severity=Severity.HIGH,
                    message=f"Date of expiry '{expiry_str}' is on or before date of issue '{issue_str}'.",
                    field="date_of_expiry",
                    ocr_value=expiry_str
                ))
                mismatches.append(MismatchItem(
                    field="date_of_expiry",
                    type="INVALID_EXPIRY_INTERVAL",
                    severity=Severity.HIGH,
                    message="Expiry date must be after issue date",
                    ocr_value=expiry_str
                ))

        if not checks:
            checks.append(CheckResult(
                rule=self.rule_name,
                status=RuleStatus.PASS,
                severity=Severity.LOW,
                message="Date validation passed."
            ))

        return checks, mismatches
