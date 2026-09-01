"""
insert_synthetic_records.py

Inserts synthetic reference records into the SQLite validation DB
so that OCR validation returns database_match=True for the sample images.

Run AFTER run_ocr_test.py has produced response.json.
"""
import sys, json, os, uuid, sqlite3
from pathlib import Path

sys.path.insert(0, 'backend')
from app.module2_validation.database.connection import get_db_connection, init_db
from app.module2_validation.config.settings import DATABASE_PATH

# Ensure tables exist
init_db()

print(f"Using DB at: {DATABASE_PATH}")

# ── Load OCR output from response.json ──────────────────────────────────────
response_path = Path('response.json')
if not response_path.exists():
    print("ERROR: response.json not found. Run run_ocr_test.py first.")
    sys.exit(1)

with open(response_path, 'r') as f:
    responses = json.load(f)

conn = get_db_connection()

def insert(conn, table, data):
    data['id'] = str(uuid.uuid4())
    data['status'] = 'ACTIVE'
    cols = ', '.join(data.keys())
    placeholders = ', '.join(['?' for _ in data])
    sql = f"INSERT OR REPLACE INTO {table} ({cols}) VALUES ({placeholders})"
    try:
        conn.execute(sql, list(data.values()))
        conn.commit()
        print(f"  ✅ Inserted into '{table}' -> id_key={list(data.values())[1]}")
    except sqlite3.Error as e:
        print(f"  ❌ Error inserting into '{table}': {e}")

# ── 1. PASSPORT ──────────────────────────────────────────────────────────────
if 'passport' in responses and 'error' not in responses['passport']:
    f = responses['passport']['fields']
    insert(conn, 'passports', {
        'passport_number': f.get('passport_number'),
        'name':            f.get('name'),
        'surname':         f.get('surname', ''),
        'nationality':     f.get('nationality'),
        'date_of_birth':   f.get('date_of_birth'),
        'date_of_issue':   f.get('date_of_issue', ''),
        'date_of_expiry':  f.get('date_of_expiry'),
        'gender':          f.get('gender'),
    })

# ── 2. AADHAAR ───────────────────────────────────────────────────────────────
if 'aadhaar' in responses and 'error' not in responses['aadhaar']:
    f = responses['aadhaar']['fields']
    insert(conn, 'aadhaars', {
        'aadhaar_number': f.get('aadhaar_number'),
        'name':           f.get('name', ''),
        'date_of_birth':  f.get('date_of_birth', ''),
        'gender':         f.get('gender', ''),
    })

# ── 3. VISA ──────────────────────────────────────────────────────────────────
if 'visa' in responses and 'error' not in responses['visa']:
    f = responses['visa']['fields']
    insert(conn, 'visas', {
        'visa_number':     f.get('visa_number'),
        'passport_number': f.get('passport_number', ''),
        'name':            f.get('name', ''),
        'nationality':     f.get('nationality', ''),
        'visa_type':       f.get('visa_type', ''),
        'date_of_birth':   f.get('date_of_birth', ''),
        'date_of_issue':   f.get('date_of_issue', ''),
        'date_of_expiry':  f.get('date_of_expiry', ''),
        'gender':          f.get('gender', ''),
    })

# ── 4. DRIVING LICENSE ───────────────────────────────────────────────────────
if 'driving_license' in responses and 'error' not in responses['driving_license']:
    f = responses['driving_license']['fields']
    insert(conn, 'driving_licenses', {
        'license_number': f.get('license_number'),
        'name':           f.get('name', ''),
        'date_of_birth':  f.get('date_of_birth', ''),
        'date_of_issue':  f.get('date_of_issue', ''),
        'date_of_expiry': f.get('date_of_expiry', ''),
        'blood_group':    f.get('blood_group', ''),
    })

# ── 5. NATIONAL ID ───────────────────────────────────────────────────────────
if 'national_id' in responses and 'error' not in responses['national_id']:
    f = responses['national_id']['fields']
    insert(conn, 'national_ids', {
        'id_number':     f.get('id_number') or f.get('name', 'UNKNOWN'),
        'name':          f.get('name', ''),
        'nationality':   f.get('nationality', ''),
        'date_of_birth': f.get('date_of_birth', ''),
        'date_of_expiry':f.get('date_of_expiry', ''),
        'gender':        f.get('gender', ''),
    })

# ── 6. PERMIT ────────────────────────────────────────────────────────────────
if 'permit' in responses and 'error' not in responses['permit']:
    f = responses['permit']['fields']
    insert(conn, 'permits', {
        'permit_number':  f.get('permit_number'),
        'name':           f.get('name', ''),
        'permit_type':    f.get('permit_type', ''),
        'passport_number':f.get('passport_number', ''),
        'date_of_issue':  f.get('date_of_issue', ''),
        'date_of_expiry': f.get('date_of_expiry', ''),
    })

conn.close()

# ── Show all inserted counts ──────────────────────────────────────────────────
conn2 = get_db_connection()
for tbl in ['passports', 'visas', 'aadhaars', 'driving_licenses', 'national_ids', 'permits']:
    row = conn2.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()
    print(f"  {tbl:25s}: {row[0]} records")
conn2.close()
print("\nDone! Now re-run run_ocr_test.py to see database_match=True in response.json")
