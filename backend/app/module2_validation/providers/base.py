"""
base.py

Abstract Base Class for reference data providers.
The validation engine only interacts through `find_document(...)` and does not care about data source.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional

from app.module2_validation.schemas.common import DataSource


class DocumentDataProvider(ABC):
    """
    Interface for document reference data sources (synthetic, government, hybrid).
    """

    source_type: DataSource = DataSource.NONE

    @abstractmethod
    def find_document(self, document_type: str, identifier: str) -> tuple[Optional[dict[str, Any]], DataSource, str]:
        """
        Finds a document reference record by document_type and primary identifier.

        Returns:
            (record_dict_or_none, data_source_enum, source_status_string)
        """
        pass
