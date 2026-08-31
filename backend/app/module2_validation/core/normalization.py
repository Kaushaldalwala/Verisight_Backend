"""
normalization.py

Field-aware OCR normalization layer.

Provides specific normalization methods for:
- Names (cleans punctuation, multiple spaces, upper-cases)
- Identifiers (maps O->0, I->1, S->5, B->8 in numeric contexts)
- Dates (parses multiple date formats YYYY-MM-DD, DD/MM/YYYY, etc.)
- Gender (maps M/F/Male/Female/0/1 to standard M/F)
"""

import re
from datetime import datetime
from typing import Any, Optional
from difflib import SequenceMatcher
from dateutil import parser as date_parser

from app.module2_validation.config.settings import FUZZY_NAME_THRESHOLD


class FieldNormalizer:
    """
    Normalizes extracted OCR fields cleanly while preserving original OCR values.
    """

    @staticmethod
    def normalize_name(value: Optional[str]) -> str:
        if not value:
            return ""
        val = str(value).upper().replace("<", " ")
        val = re.sub(r"[^A-Z ]", " ", val)
        return re.sub(r"\s+", " ", val).strip()

    @staticmethod
    def normalize_identifier(value: Optional[str]) -> str:
        if not value:
            return ""
        val = str(value).upper().replace(" ", "").replace("-", "")
        # Filter non-alphanumeric
        return re.sub(r"[^A-Z0-9]", "", val)

    @classmethod
    def normalize_numeric_identifier(cls, value: Optional[str]) -> str:
        """Fixes common OCR digit confusion O->0, I/L->1, S->5, B->8 for purely numeric IDs."""
        val = cls.normalize_identifier(value)
        substitutions = {
            'O': '0', 'Q': '0',
            'I': '1', 'L': '1', '|': '1',
            'Z': '2',
            'S': '5',
            'B': '8'
        }
        res = []
        for char in val:
            res.append(substitutions.get(char, char))
        return "".join(res)

    @staticmethod
    def normalize_date(value: Optional[str]) -> Optional[str]:
        """
        Parses date string and returns standard YYYY-MM-DD ISO format, or None.
        """
        if not value:
            return None
        val_str = str(value).strip()
        # Common OCR fixes in date strings
        val_str = val_str.replace("\\", "/").replace(".", "/")
        val_str = re.sub(r"([OQ])", "0", val_str)
        val_str = re.sub(r"([IL|])", "1", val_str)

        try:
            # Handle DD/MM/YYYY vs YYYY/MM/DD
            parsed = date_parser.parse(val_str, yearfirst=True, dayfirst=False)
            return parsed.strftime("%Y-%m-%d")
        except Exception:
            try:
                parsed = date_parser.parse(val_str, dayfirst=True)
                return parsed.strftime("%Y-%m-%d")
            except Exception:
                return None

    @staticmethod
    def normalize_gender(value: Optional[str]) -> str:
        if not value:
            return "UNKNOWN"
        val = str(value).strip().upper()
        if val in ("M", "MALE", "BOY", "0"):
            return "M"
        if val in ("F", "FEMALE", "GIRL", "1"):
            return "F"
        if "TRANS" in val:
            return "TRANSGENDER"
        return val[:1]

    @classmethod
    def fuzzy_match_names(cls, name1: str, name2: str, threshold: float = FUZZY_NAME_THRESHOLD) -> tuple[bool, float]:
        norm1 = cls.normalize_name(name1)
        norm2 = cls.normalize_name(name2)
        if not norm1 or not norm2:
            return False, 0.0
        ratio = SequenceMatcher(None, norm1, norm2).ratio() * 100.0
        return ratio >= threshold, round(ratio, 2)

    @classmethod
    def normalize_all_fields(cls, fields: dict[str, Any]) -> dict[str, Any]:
        """Returns a normalized copy of all fields."""
        normalized: dict[str, Any] = {}
        for key, val in fields.items():
            if not val:
                continue
            k_lower = key.lower()
            if "name" in k_lower:
                normalized[key] = cls.normalize_name(str(val))
            elif "date" in k_lower or "dob" in k_lower or "expiry" in k_lower or "issue" in k_lower:
                norm_date = cls.normalize_date(str(val))
                normalized[key] = norm_date if norm_date else str(val)
            elif "gender" in k_lower or "sex" in k_lower:
                normalized[key] = cls.normalize_gender(str(val))
            elif "number" in k_lower or "id" in k_lower:
                normalized[key] = cls.normalize_identifier(str(val))
            else:
                normalized[key] = str(val).strip()
        return normalized
