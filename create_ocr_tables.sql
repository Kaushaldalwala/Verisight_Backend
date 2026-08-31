-- ===========================================================
-- VeriSight Phase 1: OCR Structured Tables
-- Run this in your Supabase Dashboard > SQL Editor
-- These tables store the structured OCR extraction results
-- ===========================================================

-- 1. Passport Structured Table
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
    country             TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. Aadhaar Structured Table
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
    country         TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 3. Visa Structured Table
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
    country             TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 4. Driving License Structured Table
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
    vehicle_classes     TEXT,
    issuing_authority   TEXT,
    nationality         TEXT,
    country             TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 5. National ID Structured Table
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
    country             TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 6. Permit Structured Table
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
    country             TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ===========================================================
-- INDEXES
-- ===========================================================
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

-- ===========================================================
-- ROW LEVEL SECURITY
-- ===========================================================
ALTER TABLE ocr_passports ENABLE ROW LEVEL SECURITY;
ALTER TABLE ocr_aadhaars ENABLE ROW LEVEL SECURITY;
ALTER TABLE ocr_visas ENABLE ROW LEVEL SECURITY;
ALTER TABLE ocr_driving_licenses ENABLE ROW LEVEL SECURITY;
ALTER TABLE ocr_national_ids ENABLE ROW LEVEL SECURITY;
ALTER TABLE ocr_permits ENABLE ROW LEVEL SECURITY;

-- Select own records
CREATE POLICY "ocr_passports_select_own" ON ocr_passports FOR SELECT USING (auth.uid() = officer_id);
CREATE POLICY "ocr_aadhaars_select_own" ON ocr_aadhaars FOR SELECT USING (auth.uid() = officer_id);
CREATE POLICY "ocr_visas_select_own" ON ocr_visas FOR SELECT USING (auth.uid() = officer_id);
CREATE POLICY "ocr_driving_licenses_select_own" ON ocr_driving_licenses FOR SELECT USING (auth.uid() = officer_id);
CREATE POLICY "ocr_national_ids_select_own" ON ocr_national_ids FOR SELECT USING (auth.uid() = officer_id);
CREATE POLICY "ocr_permits_select_own" ON ocr_permits FOR SELECT USING (auth.uid() = officer_id);

-- Service role insert
CREATE POLICY "ocr_passports_service_insert" ON ocr_passports FOR INSERT WITH CHECK (true);
CREATE POLICY "ocr_aadhaars_service_insert" ON ocr_aadhaars FOR INSERT WITH CHECK (true);
CREATE POLICY "ocr_visas_service_insert" ON ocr_visas FOR INSERT WITH CHECK (true);
CREATE POLICY "ocr_driving_licenses_service_insert" ON ocr_driving_licenses FOR INSERT WITH CHECK (true);
CREATE POLICY "ocr_national_ids_service_insert" ON ocr_national_ids FOR INSERT WITH CHECK (true);
CREATE POLICY "ocr_permits_service_insert" ON ocr_permits FOR INSERT WITH CHECK (true);
