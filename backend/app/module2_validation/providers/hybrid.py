"""
hybrid.py

Hybrid provider — attempts official Government API first; seamlessly falls back
to synthetic reference database if official API is unconfigured or unavailable.
"""

from typing import Any, Optional
from app.module2_validation.providers.base import DocumentDataProvider
from app.module2_validation.providers.government import GovernmentProvider
from app.module2_validation.providers.synthetic import SyntheticProvider
from app.module2_validation.schemas.common import DataSource


class HybridProvider(DocumentDataProvider):
    source_type = DataSource.HYBRID

    def __init__(self, db_path: str | None = None):
        self.gov_provider = GovernmentProvider()
        self.synthetic_provider = SyntheticProvider(db_path)

    def find_document(self, document_type: str, identifier: str) -> tuple[Optional[dict[str, Any]], DataSource, str]:
        # Attempt 1: Government API
        rec, source, status_msg = self.gov_provider.find_document(document_type, identifier)
        if rec is not None:
            return rec, source, status_msg

        # Fallback: Synthetic Database
        rec_syn, source_syn, status_syn = self.synthetic_provider.find_document(document_type, identifier)
        return rec_syn, source_syn, f"hybrid_fallback ({status_syn})"
