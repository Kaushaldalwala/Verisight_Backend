"""
synthetic.py

Synthetic SQLite data provider implementation.
Querying local SQLite database populated with synthetic records.
"""

from typing import Any, Optional
from app.module2_validation.providers.base import DocumentDataProvider
from app.module2_validation.database.repository import DocumentRepository
from app.module2_validation.schemas.common import DataSource


class SyntheticProvider(DocumentDataProvider):
    source_type = DataSource.SYNTHETIC_DATABASE

    def __init__(self, db_path: str | None = None):
        self.repository = DocumentRepository(db_path)

    def find_document(self, document_type: str, identifier: str) -> tuple[Optional[dict[str, Any]], DataSource, str]:
        record = self.repository.find_by_identifier(document_type, identifier)
        return record, self.source_type, "demonstration_only"
