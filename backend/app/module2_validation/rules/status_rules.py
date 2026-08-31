"""
status_rules.py

Validates status of reference document record (ACTIVE, EXPIRED, REVOKED, BLACKLISTED, etc.).
"""

from typing import Any, Optional
from app.module2_validation.rules.base import BaseValidationRule
from app.module2_validation.schemas.input import DocumentInput
from app.module2_validation.schemas.output import CheckResult, MismatchItem
from app.module2_validation.schemas.common import RuleStatus, Severity, DocumentStatus


class StatusRules(BaseValidationRule):
    rule_name = "DOCUMENT_STATUS"

    def validate(
        self,
        document: DocumentInput,
        config: dict[str, Any],
        context: Optional[dict[str, Any]] = None
    ) -> tuple[list[CheckResult], list[MismatchItem]]:
        checks: list[CheckResult] = []
        mismatches: list[MismatchItem] = []

        if not context or not context.get("reference_record"):
            return checks, mismatches

        record = context["reference_record"]
        status_str = str(record.get("status", "ACTIVE")).upper()

        if status_str == DocumentStatus.BLACKLISTED:
            checks.append(CheckResult(
                rule=self.rule_name,
                status=RuleStatus.FAIL,
                severity=Severity.CRITICAL,
                message="CRITICAL: Document is flagged as BLACKLISTED in official record.",
                field="status",
                reference_value=status_str
            ))
            mismatches.append(MismatchItem(
                field="status",
                type="BLACKLISTED_DOCUMENT",
                severity=Severity.CRITICAL,
                message="Document is blacklisted",
                reference_value=status_str
            ))

        elif status_str == DocumentStatus.REVOKED:
            checks.append(CheckResult(
                rule=self.rule_name,
                status=RuleStatus.FAIL,
                severity=Severity.HIGH,
                message="Document has been REVOKED by issuing authority.",
                field="status",
                reference_value=status_str
            ))
            mismatches.append(MismatchItem(
                field="status",
                type="REVOKED_DOCUMENT",
                severity=Severity.HIGH,
                message="Document is revoked",
                reference_value=status_str
            ))

        elif status_str == DocumentStatus.EXPIRED:
            checks.append(CheckResult(
                rule=self.rule_name,
                status=RuleStatus.FAIL,
                severity=Severity.HIGH,
                message="Document status is EXPIRED in reference record.",
                field="status",
                reference_value=status_str
            ))
            mismatches.append(MismatchItem(
                field="status",
                type="EXPIRED_DOCUMENT",
                severity=Severity.HIGH,
                message="Document is expired",
                reference_value=status_str
            ))

        else:
            checks.append(CheckResult(
                rule=self.rule_name,
                status=RuleStatus.PASS,
                severity=Severity.LOW,
                message=f"Document status is '{status_str}'.",
                field="status",
                reference_value=status_str
            ))

        return checks, mismatches
