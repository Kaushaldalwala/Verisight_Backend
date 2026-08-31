"""
rule_engine.py

Generic rule engine that loads modular rule implementations and executes them.
"""

from typing import Any, Optional
import logging

from app.module2_validation.rules.base import BaseValidationRule
from app.module2_validation.rules.required_fields import RequiredFieldsRule
from app.module2_validation.rules.format_rules import FormatRules
from app.module2_validation.rules.type_rules import TypeRules
from app.module2_validation.rules.date_rules import DateRules
from app.module2_validation.rules.consistency_rules import ConsistencyRules
from app.module2_validation.rules.database_rules import DatabaseRules
from app.module2_validation.rules.status_rules import StatusRules
from app.module2_validation.schemas.input import DocumentInput
from app.module2_validation.schemas.output import CheckResult, MismatchItem

logger = logging.getLogger(__name__)


class RuleEngine:
    """
    Executes configured pipeline of validation rules dynamically.
    """

    def __init__(self, rules: list[BaseValidationRule] | None = None):
        if rules is not None:
            self.rules = rules
        else:
            self.rules = [
                RequiredFieldsRule(),
                FormatRules(),
                TypeRules(),
                DateRules(),
                ConsistencyRules(),
                DatabaseRules(),
                StatusRules(),
            ]

    def execute(
        self,
        document: DocumentInput,
        config: dict[str, Any],
        context: Optional[dict[str, Any]] = None
    ) -> tuple[list[CheckResult], list[MismatchItem]]:
        all_checks: list[CheckResult] = []
        all_mismatches: list[MismatchItem] = []

        for rule in self.rules:
            try:
                checks, mismatches = rule.validate(document, config, context)
                all_checks.extend(checks)
                all_mismatches.extend(mismatches)
            except Exception as exc:
                logger.error("Error executing rule %s: %s", getattr(rule, "rule_name", rule), exc, exc_info=True)

        return all_checks, all_mismatches
