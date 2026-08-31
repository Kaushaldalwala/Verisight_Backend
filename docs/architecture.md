# VeriSight System Architecture

VeriSight is an AI-powered document verification platform designed for automated screening of passports, visas, national IDs, driving licenses, and permits.

---

## High-Level Pipeline Architecture & Data Flow

```mermaid
flowchart TD
    subgraph ClientLayer["Client & Ingestion Layer"]
        A["Document Image / Payload Upload"] --> B["FastAPI Backend (main.py)"]
        B --> C["Authentication Middleware (JWT Bearer)"]
    end

    subgraph Module1["Module 1 — OCR Extraction"]
        C --> D["Document Wrapper Selector"]
        D -->|Passport| M1P["PassportOCR (MRZ Parser)"]
        D -->|Visa| M1V["VisaOCR (Multi-Pass EasyOCR)"]
        D -->|Aadhaar| M1A["AadhaarOCR (Verhoeff Checksum)"]
        D -->|Driving License| M1DL["DrivingLicenseOCR (Region OCR)"]
        D -->|National ID| M1NID["NationalIDOCR (Generic Layout)"]
        D -->|Permit| M1PR["PermitOCR (Generic Layout)"]

        M1P & M1V & M1A & M1DL & M1NID & M1PR --> E["Raw Extraction Output"]
        E --> Log["Supabase Scan Logger (audit log)"]
    end

    subgraph Bridge["Normalization Adapter"]
        E --> F["OCROutputAdapter (adapter.py)"]
        F -->|Field Normalization| G["Normalized DocumentInput"]
    end

    subgraph Module2["Module 2 — Document Validation Engine"]
        G --> H["ValidationEngine (validator.py)"]
        
        subgraph ConfigSystem["Dynamic Configuration System"]
            YAML["YAML Document Configs (config/document_types/*.yaml)"]
            SETTINGS["Settings & Penalties (.env / settings.py)"]
            YAML --> H
            SETTINGS --> H
        end

        subgraph ProviderLayer["Provider Abstraction Layer"]
            H --> PROVIDER{"DocumentDataProvider"}
            PROVIDER -->|Gov Mode| GOV["GovernmentProvider (Gov API)"]
            PROVIDER -->|Synthetic Mode| SYN["SyntheticProvider (SQLite DB)"]
            PROVIDER -->|Hybrid Mode| HYB["HybridProvider (Gov -> Synthetic)"]
            
            SYN --> DB[("Indexed SQLite Database\n40,000 Synthetic Records")]
            HYB --> DB
        end

        subgraph RuleEngine["Modular Validation Rule Engine"]
            H --> RE["RuleEngine (rule_engine.py)"]
            RE --> R1["RequiredFieldsRule"]
            RE --> R2["FormatRules (Regex Patterns)"]
            RE --> R3["TypeRules (Date / Enum)"]
            RE --> R4["DateRules (DOB / Expiry Sanity)"]
            RE --> R5["ConsistencyRules (Cross-Field)"]
            RE --> R6["DatabaseRules (Reference Compare)"]
            RE --> R7["StatusRules (Active / Expired / Revoked / Blacklisted)"]
        end

        subgraph ScoringSystem["Dynamic Scoring Engine"]
            R1 & R2 & R3 & R4 & R5 & R6 & R7 --> SCORE["ScoringEngine (scoring.py)"]
            SCORE --> SCORE_CALC["Calculate Penalty Weight & Clamp Score (0-100)"]
        end
    end

    subgraph OutputLayer["Unified API / CLI Output"]
        SCORE_CALC --> OUT["ValidationResult / OCRResponse"]
        OUT --> API_RES["JSON API Response (POST /api/v1/validate)"]
        OUT --> CLI_RES["Human-Readable CLI Output"]
    end

    style Module1 fill:#f9f9ff,stroke:#6c5ce7,stroke-width:2px
    style Module2 fill:#f0fff4,stroke:#00b894,stroke-width:2px
    style Bridge fill:#fff5f5,stroke:#e17055,stroke-width:2px
    style ProviderLayer fill:#fff8e7,stroke:#fdcb6e,stroke-width:2px
    style RuleEngine fill:#f0f8ff,stroke:#0984e3,stroke-width:2px
```

---

## Core Principles

1. **Fully Dynamic & Configuration-Driven:** All document types, required fields, format patterns, scoring weights, and rules are defined in YAML (`config/document_types/*.yaml`). Zero hardcoded `if doc_type == "passport"` branches in core validation logic.
2. **Provider Abstraction:** The `DocumentDataProvider` interface decouples reference lookup from data source. Supports `SyntheticProvider` (SQLite database with 35K+ seeded records), `GovernmentProvider` (official API integration architecture), and `HybridProvider`.
3. **Field-Aware Normalization:** Normalizes OCR digit/letter confusion (e.g. `O ↔ 0`, `I ↔ 1`, `S ↔ 5`, `B ↔ 8`) for numbers, cleans dates, and performs fuzzy name matching (`SequenceMatcher`).
4. **Scoring & Status Engine:** Calculates risk score (0–100) dynamically using configurable penalty weights from settings.
5. **Security Controls:** Never bypasses authentication, never uses leaked data, clearly labels synthetic data.
