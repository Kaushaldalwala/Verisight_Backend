"""
models.py

SQLite table schemas for synthetic validation database.
Uses indexes on all identifier columns for optimal lookup performance.
"""

CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS passports (
    id TEXT PRIMARY KEY,
    passport_number TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    surname TEXT,
    nationality TEXT NOT NULL,
    date_of_birth TEXT NOT NULL,
    date_of_issue TEXT,
    date_of_expiry TEXT NOT NULL,
    gender TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_passports_number ON passports(passport_number);
CREATE INDEX IF NOT EXISTS idx_passports_status ON passports(status);

CREATE TABLE IF NOT EXISTS visas (
    id TEXT PRIMARY KEY,
    visa_number TEXT UNIQUE NOT NULL,
    passport_number TEXT NOT NULL,
    name TEXT NOT NULL,
    nationality TEXT NOT NULL,
    visa_type TEXT,
    date_of_birth TEXT,
    date_of_issue TEXT,
    date_of_expiry TEXT NOT NULL,
    gender TEXT,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_visas_number ON visas(visa_number);
CREATE INDEX IF NOT EXISTS idx_visas_passport ON visas(passport_number);

CREATE TABLE IF NOT EXISTS aadhaars (
    id TEXT PRIMARY KEY,
    aadhaar_number TEXT UNIQUE NOT NULL,
    name TEXT,
    date_of_birth TEXT,
    gender TEXT,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_aadhaars_number ON aadhaars(aadhaar_number);

CREATE TABLE IF NOT EXISTS driving_licenses (
    id TEXT PRIMARY KEY,
    license_number TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    date_of_birth TEXT NOT NULL,
    date_of_issue TEXT,
    date_of_expiry TEXT NOT NULL,
    blood_group TEXT,
    relation TEXT,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_driving_licenses_number ON driving_licenses(license_number);

CREATE TABLE IF NOT EXISTS national_ids (
    id TEXT PRIMARY KEY,
    id_number TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    nationality TEXT,
    date_of_birth TEXT,
    date_of_expiry TEXT,
    gender TEXT,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_national_ids_number ON national_ids(id_number);

CREATE TABLE IF NOT EXISTS permits (
    id TEXT PRIMARY KEY,
    permit_number TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    permit_type TEXT,
    passport_number TEXT,
    date_of_issue TEXT,
    date_of_expiry TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_permits_number ON permits(permit_number);
"""
