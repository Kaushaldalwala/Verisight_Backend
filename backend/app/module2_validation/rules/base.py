"""
base.py

Abstract Base Class for modular validation rules.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional

from app.module2_validation.schemas.input import DocumentInput
from app.module2_validation.schemas.output import CheckResult, MismatchItem


class BaseValidationRule(ABC):
    """
    Interface for all modular validation rules in Module 2.
    """

    rule_name: str = "BASE_RULE"

    @abstractmethod
    def validate(
        self,
        document: DocumentInput,
        config: dict[str, Any],
        context: Optional[dict[str, Any]] = None
    ) -> tuple[list[CheckResult], list[MismatchItem]]:
        """
        Executes the rule check against document input and config.
        Returns (list_of_check_results, list_of_mismatches).
        """
        pass
