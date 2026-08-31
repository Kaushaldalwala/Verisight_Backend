# Module 2 — Document Validation Engine Documentation

VeriSight Module 2 provides automated, rule-based, and reference-database document validation for identity and travel documents.

---

## Features

- **YAML Configuration-Driven:** Document rules, required fields, format regex, and cross-field constraints managed per document type in `config/document_types/*.yaml`.
- **Modular Rule Pipeline:** Executes required fields, format patterns, field types, date sanity, cross-field consistency, database lookups, and document status checks.
- **Provider Abstraction:** `SyntheticProvider` (SQLite database with 35,000+ records), `GovernmentProvider`, and `HybridProvider`.
- **Field Normalization & Fuzzy Matching:** OCR error correction (digit/char confusion) and string similarity matching for names.
- **Dynamic Scoring:** Calculates score (0–100) and recommendation (`PASS`, `MANUAL_REVIEW`, `FAIL`) using configurable penalty weights.

---

## API Usage

### Endpoint: `POST /api/v1/validate`
**Headers:** `Authorization: Bearer <access_token>`

**Request Body:**
```json
{
  "document_type": "passport",
  "fields": {
    "name": "ARJUN MEHTA",
    "passport_number": "P0000001",
    "nationality": "IND",
    "date_of_birth": "1998-04-12",
    "date_of_expiry": "2033-04-11",
    "gender": "M"
  }
}
```

**Response Body:**
```json
{
  "request_id": "8f3b2a11-9c8d-4e2b-9a1d-3f4e5a6b7c8d",
  "document_type": "passport",
  "validation_status": "PASS",
  "validation_score": 100.0,
  "database_match": true,
  "data_source": "synthetic_database",
  "source_status": "demonstration_only",
  "document_status": "ACTIVE",
  "checks": [
    {
      "rule": "REQUIRED_FIELDS",
      "status": "PASS",
      "severity": "LOW",
      "message": "Required field 'passport_number' is present."
    }
  ],
  "mismatches": [],
  "warnings": [],
  "errors": [],
  "recommendation": "PASS",
  "processing_time_ms": 12
}
```

---

## CLI Usage

```bash
# Validate specific document by ID
python -m backend.app.module2_validation.cli.commands --document passport --id P0000001

# Seed synthetic validation database
python -m backend.app.module2_validation.database.seed --passports 10000 --visas 10000 --aadhaars 5000
```
