"""
scoring.py

Configurable validation scoring engine.

Calculates overall document risk/confidence score dynamically using configurable penalty weights.
"""

from typing import Any
from app.module2_validation.config.settings import (
    SCORING_PENALTIES,
    VALIDATION_PASS_THRESHOLD,
    MANUAL_REVIEW_THRESHOLD,
)
from app.module2_validation.schemas.common import ValidationStatus, RuleStatus, Severity


class ScoringEngine:
    """
    Computes validation score (0-100) and recommendation based on check results.
    """

    def __init__(self, penalties: dict[str, int] | None = None):
        self.penalties = penalties or SCORING_PENALTIES

    def calculate_score(self, checks: list[Any], ocr_confidence: float = 100.0) -> tuple[float, ValidationStatus]:
        base_score = 100.0
        total_penalty = 0.0

        for check in checks:
            # check can be CheckResult object or dict
            rule_name = getattr(check, "rule", "") if hasattr(check, "rule") else check.get("rule", "")
            status = getattr(check, "status", RuleStatus.PASS) if hasattr(check, "status") else check.get("status", RuleStatus.PASS)
            severity = getattr(check, "severity", Severity.LOW) if hasattr(check, "severity") else check.get("severity", Severity.LOW)

            if status in (RuleStatus.FAIL, RuleStatus.WARNING):
                penalty_key = self._map_rule_to_penalty_key(rule_name, check)
                penalty = abs(self.penalties.get(penalty_key, 15))

                if severity == Severity.CRITICAL:
                    penalty *= 1.5
                elif severity == Severity.HIGH:
                    penalty *= 1.2
                elif severity == Severity.LOW:
                    penalty *= 0.7

                total_penalty += penalty

        # Consider OCR confidence factor
        if ocr_confidence < 50.0:
            total_penalty += 15.0
        elif ocr_confidence < 70.0:
            total_penalty += 8.0

        final_score = max(0.0, min(100.0, base_score - total_penalty))

        # Status recommendation
        if final_score >= VALIDATION_PASS_THRESHOLD:
            recommendation = ValidationStatus.PASS
        elif final_score >= MANUAL_REVIEW_THRESHOLD:
            recommendation = ValidationStatus.MANUAL_REVIEW
        else:
            recommendation = ValidationStatus.FAIL

        return round(final_score, 1), recommendation

    @staticmethod
    def _map_rule_to_penalty_key(rule_name: str, check: Any) -> str:
        rule_upper = rule_name.upper()
        msg = getattr(check, "message", "") if hasattr(check, "message") else str(check)
        msg_upper = str(msg).upper()

        if "BLACKLISTED" in msg_upper or "BLACKLISTED" in rule_upper:
            return "blacklisted"
        if "REVOKED" in msg_upper or "REVOKED" in rule_upper:
            return "revoked"
        if "EXPIRED" in msg_upper or "EXPIRED" in rule_upper:
            return "expired"
        if "REQUIRED" in rule_upper:
            return "missing_required_field"
        if "FORMAT" in rule_upper:
            return "format_failure"
        if "TYPE" in rule_upper:
            return "type_failure"
        if "DATE" in rule_upper:
            return "date_failure"
        if "CROSS_FIELD" in rule_upper or "CONSISTENCY" in rule_upper:
            return "cross_field_mismatch"
        if "DATABASE_NOT_FOUND" in rule_upper:
            return "database_not_found"
        if "DATABASE" in rule_upper:
            return "database_mismatch"
        return "normalization_warning"
