"""
repository.py

Repository abstraction layer for querying reference documents.
Executes parameterized queries and uses indexes to prevent full table scans.
"""

from typing import Any, Optional
import sqlite3
import logging

from app.module2_validation.database.connection import get_db_connection, init_db

logger = logging.getLogger(__name__)


class DocumentRepository:
    """
    Thread-safe repository for document lookup.
    """

    TABLE_MAP = {
        "passport": ("passports", "passport_number"),
        "visa": ("visas", "visa_number"),
        "aadhaar": ("aadhaars", "aadhaar_number"),
        "driving_license": ("driving_licenses", "license_number"),
        "national_id": ("national_ids", "id_number"),
        "permit": ("permits", "permit_number"),
    }

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path
        # Ensure database tables exist
        init_db(self.db_path)

    def find_by_identifier(self, document_type: str, identifier: str) -> Optional[dict[str, Any]]:
        doc_type_clean = document_type.lower().strip().replace(" ", "_")
        table_info = self.TABLE_MAP.get(doc_type_clean)

        if not table_info:
            logger.warning("Repository does not have a mapped table for document_type: %s", document_type)
            return None

        table_name, id_col = table_info

        query = f"SELECT * FROM {table_name} WHERE {id_col} = ? LIMIT 1"

        conn = get_db_connection(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(query, (identifier,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
        except sqlite3.Error as err:
            logger.error("Database query error: %s", err)
            return None
        finally:
            conn.close()

    def count_records(self, document_type: str) -> int:
        doc_type_clean = document_type.lower().strip().replace(" ", "_")
        table_info = self.TABLE_MAP.get(doc_type_clean)
        if not table_info:
            return 0
        table_name, _ = table_info

        conn = get_db_connection(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            return cursor.fetchone()[0]
        finally:
            conn.close()
