-- ===========================================================
-- VeriSight Supabase Migration
-- Run this ONCE in your Supabase SQL Editor
-- Project: verisight demo
-- ===========================================================


-- -----------------------------------------------------------
-- 1. OFFICER PROFILES
-- -----------------------------------------------------------

CREATE TABLE IF NOT EXISTS officer_profiles (
    id            UUID        PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    first_name    TEXT        NOT NULL,
    last_name     TEXT        NOT NULL,
    officer_id    TEXT        UNIQUE NOT NULL,
    officer_email TEXT        UNIQUE NOT NULL,
    organization  TEXT        NOT NULL,
    designation   TEXT        NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS set_officer_profiles_updated_at ON officer_profiles;
CREATE TRIGGER set_officer_profiles_updated_at
    BEFORE UPDATE ON officer_profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


-- -----------------------------------------------------------
-- 2. SCAN LOGS
-- -----------------------------------------------------------

CREATE TABLE IF NOT EXISTS scan_logs (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    officer_id      UUID        NOT NULL REFERENCES officer_profiles(id) ON DELETE CASCADE,
    document_type   TEXT        NOT NULL,          -- passport | aadhaar | visa | driving_license | national_id | permit
    status          TEXT        NOT NULL,          -- OCR result status string
    ocr_confidence  FLOAT       DEFAULT 0.0,
    fields          JSONB       DEFAULT '{}',      -- all extracted fields
    image_filename  TEXT,                          -- original uploaded filename
    image_path      TEXT,                          -- path to stored image in Supabase storage
    processing_ms   INTEGER,                       -- time taken in milliseconds
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index for fast officer lookups
CREATE INDEX IF NOT EXISTS idx_scan_logs_officer_id ON scan_logs (officer_id);
CREATE INDEX IF NOT EXISTS idx_scan_logs_document_type ON scan_logs (document_type);
CREATE INDEX IF NOT EXISTS idx_scan_logs_created_at ON scan_logs (created_at DESC);


-- -----------------------------------------------------------
-- 3. STORAGE BUCKETS
-- -----------------------------------------------------------

-- Create a private storage bucket for scanned documents if not exists
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'scanned-documents',
    'scanned-documents',
    false,
    10485760, -- 10MB limit
    ARRAY['image/jpeg', 'image/jpg', 'image/png', 'image/webp', 'image/bmp', 'image/tiff']::text[]
)
ON CONFLICT (id) DO NOTHING;



-- -----------------------------------------------------------
-- 3. ROW LEVEL SECURITY
-- -----------------------------------------------------------

ALTER TABLE officer_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE scan_logs ENABLE ROW LEVEL SECURITY;

-- Officers can read their own profile
DROP POLICY IF EXISTS "officer_profiles_select_own" ON officer_profiles;
CREATE POLICY "officer_profiles_select_own"
    ON officer_profiles
    FOR SELECT
    USING (auth.uid() = id);

-- Officers can update their own profile
DROP POLICY IF EXISTS "officer_profiles_update_own" ON officer_profiles;
CREATE POLICY "officer_profiles_update_own"
    ON officer_profiles
    FOR UPDATE
    USING (auth.uid() = id);

-- Service role can insert profiles (used during signup)
DROP POLICY IF EXISTS "officer_profiles_service_insert" ON officer_profiles;
CREATE POLICY "officer_profiles_service_insert"
    ON officer_profiles
    FOR INSERT
    WITH CHECK (true);

-- Officers can read their own scan logs
DROP POLICY IF EXISTS "scan_logs_select_own" ON scan_logs;
CREATE POLICY "scan_logs_select_own"
    ON scan_logs
    FOR SELECT
    USING (auth.uid() = officer_id);

-- Service role can insert scan logs
DROP POLICY IF EXISTS "scan_logs_service_insert" ON scan_logs;
CREATE POLICY "scan_logs_service_insert"
    ON scan_logs
    FOR INSERT
    WITH CHECK (true);


-- -----------------------------------------------------------
-- 4. DOCUMENT-SPECIFIC STRUCTURED TABLES
-- -----------------------------------------------------------

-- Passport Structured Table  (ICAO 9303 TD1/TD2/TD3, all countries)
CREATE TABLE IF NOT EXISTS ocr_passports (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_log_id         UUID        NOT NULL REFERENCES scan_logs(id) ON DELETE CASCADE,
    officer_id          UUID        NOT NULL REFERENCES officer_profiles(id) ON DELETE CASCADE,
    passport_number     TEXT,
    name                TEXT,
    surname             TEXT,
    given_name          TEXT,
    nationality         TEXT,
    date_of_birth       TEXT,
    date_of_issue       TEXT,
    date_of_expiry      TEXT,
    gender              TEXT,
    personal_number     TEXT,
    passport_type       TEXT,
    place_of_birth      TEXT,
    issuing_authority   TEXT,
    mrz_line1           TEXT,
    mrz_line2           TEXT,
    country             TEXT,       -- ISO 3166-1 alpha-2 issuing country
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Aadhaar Structured Table
CREATE TABLE IF NOT EXISTS ocr_aadhaars (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_log_id     UUID        NOT NULL REFERENCES scan_logs(id) ON DELETE CASCADE,
    officer_id      UUID        NOT NULL REFERENCES officer_profiles(id) ON DELETE CASCADE,
    aadhaar_number  TEXT,
    masked_number   TEXT,
    name            TEXT,
    gender          TEXT,
    date_of_birth   TEXT,
    address         TEXT,
    country         TEXT,       -- always IN
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Visa Structured Table  (Schengen, US, UK, UAE, Indian, Chinese, etc.)
CREATE TABLE IF NOT EXISTS ocr_visas (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_log_id         UUID        NOT NULL REFERENCES scan_logs(id) ON DELETE CASCADE,
    officer_id          UUID        NOT NULL REFERENCES officer_profiles(id) ON DELETE CASCADE,
    visa_number         TEXT,
    control_number      TEXT,
    visa_type           TEXT,
    entries             TEXT,
    issuing_post        TEXT,
    issuing_authority   TEXT,
    annotation          TEXT,
    name                TEXT,
    surname             TEXT,
    given_name          TEXT,
    date_of_birth       TEXT,
    passport_number     TEXT,
    nationality         TEXT,
    date_of_issue       TEXT,
    date_of_expiry      TEXT,
    mrz_line1           TEXT,
    mrz_line2           TEXT,
    country             TEXT,       -- ISO 3166-1 alpha-2 issuing country
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Driving License Structured Table  (Indian, EU Directive 2006/126/EC, US, ASEAN)
CREATE TABLE IF NOT EXISTS ocr_driving_licenses (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_log_id         UUID        NOT NULL REFERENCES scan_logs(id) ON DELETE CASCADE,
    officer_id          UUID        NOT NULL REFERENCES officer_profiles(id) ON DELETE CASCADE,
    license_number      TEXT,
    name                TEXT,
    date_of_issue       TEXT,
    date_of_expiry      TEXT,
    date_of_birth       TEXT,
    blood_group         TEXT,
    relation            TEXT,
    address             TEXT,
    vehicle_classes     TEXT,       -- e.g. "A, B, C" (EU) or "LMV,MCWG" (India)
    issuing_authority   TEXT,
    nationality         TEXT,
    country             TEXT,       -- ISO 3166-1 alpha-2
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- National ID Structured Table  (EU, GCC, South Asian, African, LATAM, ASEAN)
CREATE TABLE IF NOT EXISTS ocr_national_ids (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_log_id         UUID        NOT NULL REFERENCES scan_logs(id) ON DELETE CASCADE,
    officer_id          UUID        NOT NULL REFERENCES officer_profiles(id) ON DELETE CASCADE,
    id_number           TEXT,
    name                TEXT,
    surname             TEXT,
    given_name          TEXT,
    nationality         TEXT,
    date_of_birth       TEXT,
    date_of_issue       TEXT,
    date_of_expiry      TEXT,
    gender              TEXT,
    place_of_birth      TEXT,
    address             TEXT,
    issuing_authority   TEXT,
    mrz_line1           TEXT,
    mrz_line2           TEXT,
    country             TEXT,       -- ISO 3166-1 alpha-2
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Permit Structured Table  (work/residence/travel permits from all jurisdictions)
CREATE TABLE IF NOT EXISTS ocr_permits (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_log_id         UUID        NOT NULL REFERENCES scan_logs(id) ON DELETE CASCADE,
    officer_id          UUID        NOT NULL REFERENCES officer_profiles(id) ON DELETE CASCADE,
    permit_number       TEXT,
    permit_type         TEXT,
    name                TEXT,
    surname             TEXT,
    given_name          TEXT,
    date_of_birth       TEXT,
    date_of_issue       TEXT,
    date_of_expiry      TEXT,
    gender              TEXT,
    nationality         TEXT,
    passport_number     TEXT,
    issuing_authority   TEXT,
    address             TEXT,
    mrz_line1           TEXT,
    mrz_line2           TEXT,
    country             TEXT,       -- ISO 3166-1 alpha-2 issuing country
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- -----------------------------------------------------------
-- 5. INDEXES FOR STRUCTURED TABLES
-- -----------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_ocr_passports_scan ON ocr_passports (scan_log_id);
CREATE INDEX IF NOT EXISTS idx_ocr_passports_num ON ocr_passports (passport_number);
CREATE INDEX IF NOT EXISTS idx_ocr_aadhaars_scan ON ocr_aadhaars (scan_log_id);
CREATE INDEX IF NOT EXISTS idx_ocr_aadhaars_num ON ocr_aadhaars (aadhaar_number);
CREATE INDEX IF NOT EXISTS idx_ocr_visas_scan ON ocr_visas (scan_log_id);
CREATE INDEX IF NOT EXISTS idx_ocr_visas_num ON ocr_visas (visa_number);
CREATE INDEX IF NOT EXISTS idx_ocr_dl_scan ON ocr_driving_licenses (scan_log_id);
CREATE INDEX IF NOT EXISTS idx_ocr_dl_num ON ocr_driving_licenses (license_number);
CREATE INDEX IF NOT EXISTS idx_ocr_nid_scan ON ocr_national_ids (scan_log_id);
CREATE INDEX IF NOT EXISTS idx_ocr_nid_num ON ocr_national_ids (id_number);
CREATE INDEX IF NOT EXISTS idx_ocr_permits_scan ON ocr_permits (scan_log_id);
CREATE INDEX IF NOT EXISTS idx_ocr_permits_num ON ocr_permits (permit_number);

-- -----------------------------------------------------------
-- 6. SECURITY & POLICIES FOR STRUCTURED TABLES
-- -----------------------------------------------------------
ALTER TABLE ocr_passports ENABLE ROW LEVEL SECURITY;
ALTER TABLE ocr_aadhaars ENABLE ROW LEVEL SECURITY;
ALTER TABLE ocr_visas ENABLE ROW LEVEL SECURITY;
ALTER TABLE ocr_driving_licenses ENABLE ROW LEVEL SECURITY;
ALTER TABLE ocr_national_ids ENABLE ROW LEVEL SECURITY;
ALTER TABLE ocr_permits ENABLE ROW LEVEL SECURITY;

-- Select own document records policies
CREATE POLICY "ocr_passports_select_own" ON ocr_passports FOR SELECT USING (auth.uid() = officer_id);
CREATE POLICY "ocr_aadhaars_select_own" ON ocr_aadhaars FOR SELECT USING (auth.uid() = officer_id);
CREATE POLICY "ocr_visas_select_own" ON ocr_visas FOR SELECT USING (auth.uid() = officer_id);
CREATE POLICY "ocr_driving_licenses_select_own" ON ocr_driving_licenses FOR SELECT USING (auth.uid() = officer_id);
CREATE POLICY "ocr_national_ids_select_own" ON ocr_national_ids FOR SELECT USING (auth.uid() = officer_id);
CREATE POLICY "ocr_permits_select_own" ON ocr_permits FOR SELECT USING (auth.uid() = officer_id);

-- Service role insert policies
CREATE POLICY "ocr_passports_service_insert" ON ocr_passports FOR INSERT WITH CHECK (true);
CREATE POLICY "ocr_aadhaars_service_insert" ON ocr_aadhaars FOR INSERT WITH CHECK (true);
CREATE POLICY "ocr_visas_service_insert" ON ocr_visas FOR INSERT WITH CHECK (true);
CREATE POLICY "ocr_driving_licenses_service_insert" ON ocr_driving_licenses FOR INSERT WITH CHECK (true);
CREATE POLICY "ocr_national_ids_service_insert" ON ocr_national_ids FOR INSERT WITH CHECK (true);
CREATE POLICY "ocr_permits_service_insert" ON ocr_permits FOR INSERT WITH CHECK (true);

