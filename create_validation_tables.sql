-- VeriSight Phase 1: Validation Tables
-- Run this SQL in your Supabase Dashboard > SQL Editor


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
