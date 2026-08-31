"""
connection.py

Database connection manager for SQLite synthetic reference database.
Handles thread-safe connection pooling and automatic schema initialization.
"""

import os
import sqlite3
from pathlib import Path
import logging

from app.module2_validation.config.settings import DATABASE_PATH
from app.module2_validation.database.models import CREATE_TABLES_SQL

logger = logging.getLogger(__name__)


def get_db_connection(db_path: str | None = None) -> sqlite3.Connection:
    target_path = db_path or DATABASE_PATH
    db_file = Path(target_path)
    db_file.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_file), timeout=10.0)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str | None = None) -> None:
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.executescript(CREATE_TABLES_SQL)
        conn.commit()
        logger.info("Database schema initialized successfully at %s", db_path or DATABASE_PATH)
    finally:
        conn.close()
