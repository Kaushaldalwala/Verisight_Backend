"""
settings.py

Centralized configuration settings for Module 2 Document Validation.

All thresholds, scoring weights, database paths, and document rules are configurable
without editing Python code.
"""

import os
from pathlib import Path
from typing import Any, Dict
import yaml

from dotenv import load_dotenv

load_dotenv()

# Base paths
BASE_DIR = Path(__file__).resolve().parents[3]  # VeriSight/backend
DOC_TYPES_DIR = Path(__file__).resolve().parent / "document_types"

# Database Configuration
DATABASE_PATH = os.getenv(
    "VALIDATION_DB_PATH",
    str(BASE_DIR / "data" / "synthetic_validation.db")
)

# Data Provider Mode: synthetic | government | hybrid
DATA_PROVIDER_MODE = os.getenv("DATA_PROVIDER", "synthetic").lower()

# Government API Settings
GOV_API_URL = os.getenv("GOV_API_URL", "")
GOV_API_KEY = os.getenv("GOV_API_KEY", "")
GOV_API_SECRET = os.getenv("GOV_API_SECRET", "")

# Fuzzy Matching & Thresholds
FUZZY_NAME_THRESHOLD = float(os.getenv("FUZZY_NAME_THRESHOLD", "85.0"))
VALIDATION_PASS_THRESHOLD = float(os.getenv("VALIDATION_PASS_THRESHOLD", "80.0"))
MANUAL_REVIEW_THRESHOLD = float(os.getenv("MANUAL_REVIEW_THRESHOLD", "50.0"))

# Configurable Scoring Penalties
SCORING_PENALTIES = {
    "missing_required_field": int(os.getenv("PENALTY_MISSING_REQUIRED", "-20")),
    "format_failure": int(os.getenv("PENALTY_FORMAT_FAILURE", "-15")),
    "type_failure": int(os.getenv("PENALTY_TYPE_FAILURE", "-10")),
    "date_failure": int(os.getenv("PENALTY_DATE_FAILURE", "-25")),
    "cross_field_mismatch": int(os.getenv("PENALTY_CROSS_FIELD_MISMATCH", "-30")),
    "database_not_found": int(os.getenv("PENALTY_DATABASE_NOT_FOUND", "-30")),
    "database_mismatch": int(os.getenv("PENALTY_DATABASE_MISMATCH", "-25")),
    "expired": int(os.getenv("PENALTY_EXPIRED", "-25")),
    "revoked": int(os.getenv("PENALTY_REVOKED", "-40")),
    "blacklisted": int(os.getenv("PENALTY_BLACKLISTED", "-50")),
    "unknown_document": int(os.getenv("PENALTY_UNKNOWN_DOC", "-40")),
    "normalization_warning": int(os.getenv("PENALTY_NORMALIZATION_WARN", "-5")),
}


class DocumentConfigLoader:
    """Dynamically loads and caches document-type YAML configurations."""

    _cache: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def load_config(cls, document_type: str) -> Dict[str, Any]:
        doc_type_clean = document_type.lower().strip().replace(" ", "_")

        if doc_type_clean in cls._cache:
            return cls._cache[doc_type_clean]

        yaml_file = DOC_TYPES_DIR / f"{doc_type_clean}.yaml"

        if not yaml_file.exists():
            # Fallback default configuration for unknown document types
            config = cls._get_default_fallback_config(doc_type_clean)
        else:
            with open(yaml_file, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}

        cls._cache[doc_type_clean] = config
        return config

    @classmethod
    def get_supported_types(cls) -> list[str]:
        if not DOC_TYPES_DIR.exists():
            return ["passport", "visa", "aadhaar", "driving_license", "national_id", "permit"]
        return [f.stem for f in DOC_TYPES_DIR.glob("*.yaml")]

    @staticmethod
    def _get_default_fallback_config(document_type: str) -> Dict[str, Any]:
        return {
            "document_type": document_type,
            "display_name": document_type.replace("_", " ").title(),
            "identifier_field": "document_number",
            "fields": {
                "document_number": {"required": True, "type": "identifier"},
                "name": {"required": True, "type": "string"},
                "date_of_expiry": {"required": False, "type": "date"},
            },
            "cross_field_rules": [],
            "_disclaimer": "Fallback prototype configuration for unlisted document type"
        }
