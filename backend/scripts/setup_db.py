"""
setup_db.py

Initializes Supabase validation tables and inserts synthetic data.
Uses the Supabase REST API (no direct PostgreSQL connection required).
"""

import os
import sys
import json
import random
from datetime import datetime, timedelta
from dotenv import load_dotenv
import logging
import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("setup_db")

# Load .env from the project root (two levels up from this script)
env_path = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
env_path = os.path.abspath(env_path)
load_dotenv(env_path)

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
SUPABASE_SECRET_KEY = os.environ.get("SUPABASE_SECRET_KEY")

# Use the secret key (service role) for admin operations, fall back to anon key
API_KEY = SUPABASE_SECRET_KEY or SUPABASE_KEY

if not SUPABASE_URL or not API_KEY:
    logger.error("Missing SUPABASE_URL or SUPABASE_KEY/SUPABASE_SECRET_KEY in .env file.")
    logger.error(f"Looked for .env at: {env_path}")
    sys.exit(1)

HEADERS = {
    "apikey": API_KEY,
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal"
}

# ---------------------------------------------------------------
# Table creation SQL
# ---------------------------------------------------------------
TABLE_SQL = """
CREATE TABLE IF NOT EXISTS val_aadhar_details (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    aadhaar_number TEXT UNIQUE,
    name TEXT,
    gender TEXT,
    date_of_birth TEXT,
    address TEXT,
    status TEXT DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS val_driving_license_details (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    license_number TEXT UNIQUE,
    name TEXT,
    date_of_birth TEXT,
    date_of_issue TEXT,
    date_of_expiry TEXT,
    vehicle_classes TEXT,
    status TEXT DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS val_national_id_details (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    id_number TEXT UNIQUE,
    name TEXT,
    date_of_birth TEXT,
    gender TEXT,
    nationality TEXT,
    status TEXT DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS val_passport_details (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    passport_number TEXT UNIQUE,
    name TEXT,
    date_of_birth TEXT,
    gender TEXT,
    nationality TEXT,
    date_of_issue TEXT,
    date_of_expiry TEXT,
    status TEXT DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS val_permit_details (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    permit_number TEXT UNIQUE,
    permit_type TEXT,
    name TEXT,
    date_of_birth TEXT,
    nationality TEXT,
    status TEXT DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS val_visa_details (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    visa_number TEXT UNIQUE,
    visa_type TEXT,
    name TEXT,
    date_of_birth TEXT,
    nationality TEXT,
    status TEXT DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""


def random_date(start_year=1970, end_year=2000):
    start = datetime(start_year, 1, 1)
    end = datetime(end_year, 12, 31)
    return (start + timedelta(days=random.randint(0, (end - start).days))).strftime("%d/%m/%Y")


def create_tables_via_sql_editor():
    """
    Try to create tables via the Supabase pg REST endpoint.
    If that endpoint is unavailable, print manual instructions.
    """
    logger.info("Attempting to create validation tables...")

    # Try the Supabase SQL endpoint (available on newer Supabase versions)
    sql_url = f"{SUPABASE_URL}/rest/v1/rpc"

    # Split SQL into individual CREATE TABLE statements
    statements = [s.strip() for s in TABLE_SQL.split(";") if s.strip()]

    # First, check if tables already exist by trying a simple select
    test_url = f"{SUPABASE_URL}/rest/v1/val_aadhar_details?select=id&limit=1"
    try:
        resp = httpx.get(test_url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            logger.info("Validation tables already exist. Skipping creation.")
            return True
        elif resp.status_code == 404:
            # Table doesn't exist, need to create it
            logger.info("Tables not found. They need to be created.")
        else:
            logger.info(f"Table check returned status {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        logger.warning(f"Could not check tables: {e}")

    # Print instructions for manual creation
    logger.warning("=" * 60)
    logger.warning("MANUAL STEP REQUIRED: Create validation tables")
    logger.warning("=" * 60)
    logger.warning("")
    logger.warning("Go to your Supabase Dashboard:")
    logger.warning(f"  {SUPABASE_URL.replace('.co', '.co').rstrip('/')}")
    logger.warning("")
    logger.warning("1. Click 'SQL Editor' in the left sidebar")
    logger.warning("2. Click 'New Query'")
    logger.warning("3. Paste the SQL from: versight_phase_1/create_validation_tables.sql")
    logger.warning("4. Click 'Run'")
    logger.warning("")
    logger.warning("=" * 60)

    # Also write the SQL to a convenient file
    sql_file_path = os.path.join(os.path.dirname(__file__), "..", "..", "create_validation_tables.sql")
    sql_file_path = os.path.abspath(sql_file_path)
    with open(sql_file_path, "w", encoding="utf-8") as f:
        f.write("-- VeriSight Phase 1: Validation Tables\n")
        f.write("-- Run this SQL in your Supabase Dashboard > SQL Editor\n\n")
        f.write(TABLE_SQL)
    logger.info(f"SQL file saved to: {sql_file_path}")

    return False


def insert_data_via_rest(table_name, rows):
    """Insert rows using the Supabase REST API (PostgREST)."""
    url = f"{SUPABASE_URL}/rest/v1/{table_name}"
    headers = {**HEADERS, "Prefer": "resolution=ignore-duplicates,return=minimal"}

    try:
        resp = httpx.post(url, headers=headers, json=rows, timeout=30)
        if resp.status_code in [200, 201, 204]:
            logger.info(f"  ✓ Inserted {len(rows)} rows into {table_name}")
            return True
        elif resp.status_code == 409:
            logger.info(f"  ✓ {table_name}: Data already exists (skipped duplicates)")
            return True
        else:
            logger.error(f"  ✗ {table_name}: HTTP {resp.status_code} - {resp.text[:200]}")
            return False
    except Exception as e:
        logger.error(f"  ✗ {table_name}: {e}")
        return False


def insert_synthetic_data():
    """Insert 50 rows of synthetic data into each validation table."""
    logger.info("Inserting synthetic data into validation tables...")

    # 1. Aadhaar
    rows = []
    for i in range(50):
        rows.append({
            "aadhaar_number": f"1234567890{i:02d}",
            "name": f"Test User {i}",
            "gender": random.choice(["MALE", "FEMALE"]),
            "date_of_birth": random_date(),
            "address": f"123 Fake Street, City {i}, State"
        })
    insert_data_via_rest("val_aadhar_details", rows)

    # 2. Driving License
    rows = []
    for i in range(50):
        rows.append({
            "license_number": f"DL-123456789-{i}",
            "name": f"Driver {i}",
            "date_of_birth": random_date(),
            "date_of_issue": random_date(2010, 2020),
            "date_of_expiry": random_date(2030, 2040),
            "vehicle_classes": "LMV, MCWG"
        })
    insert_data_via_rest("val_driving_license_details", rows)

    # 3. National ID
    rows = []
    for i in range(50):
        rows.append({
            "id_number": f"NID-987654-{i}",
            "name": f"Citizen {i}",
            "date_of_birth": random_date(),
            "gender": random.choice(["MALE", "FEMALE"]),
            "nationality": "IND"
        })
    insert_data_via_rest("val_national_id_details", rows)

    # 4. Passport
    rows = []
    for i in range(50):
        rows.append({
            "passport_number": f"P12345{i:02d}",
            "name": f"Traveler {i}",
            "date_of_birth": random_date(),
            "gender": random.choice(["MALE", "FEMALE"]),
            "nationality": "IND",
            "date_of_issue": random_date(2015, 2022),
            "date_of_expiry": random_date(2025, 2032)
        })
    insert_data_via_rest("val_passport_details", rows)

    # 5. Permit
    rows = []
    for i in range(50):
        rows.append({
            "permit_number": f"PER-5555-{i}",
            "permit_type": random.choice(["WORK", "RESIDENCE"]),
            "name": f"Worker {i}",
            "date_of_birth": random_date(),
            "nationality": "IND"
        })
    insert_data_via_rest("val_permit_details", rows)

    # 6. Visa
    rows = []
    for i in range(50):
        rows.append({
            "visa_number": f"V-9999-{i}",
            "visa_type": random.choice(["TOURIST", "BUSINESS"]),
            "name": f"Visitor {i}",
            "date_of_birth": random_date(),
            "nationality": "IND"
        })
    insert_data_via_rest("val_visa_details", rows)

    logger.info("Synthetic data insertion complete.")


if __name__ == "__main__":
    tables_exist = create_tables_via_sql_editor()
    if tables_exist:
        insert_synthetic_data()
    else:
        logger.warning("Please create the tables first (see instructions above), then re-run this script.")
