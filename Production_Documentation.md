# VeriSight Phase 1 - Production Documentation

## Overview

VeriSight Phase 1 is a unified backend and UI system that combines robust Optical Character Recognition (OCR) capabilities with a validation engine (Module 2). This system is designed to extract information from uploaded identification documents (Aadhaar, Passport, Visa, Driving License, National ID, Permit) and validate that extracted information against a centralized Supabase reference database.

The project consolidates the previous `ocr_modules` and `VeriSight` (which contained Module 2 Validation) into a single, cohesive application `versight_phase_1`.

## Architecture & Flow

### 1. The Pipeline Flow
1. **User Uploads Document**: A user selects a document type (e.g., AADHAAR) and uploads an image via the `/static/index.html` frontend UI.
2. **Backend API Request**: The frontend makes a POST request to `/api/v1/process-document` with the file.
3. **Module 1 (OCR Extraction)**:
   - The backend routes the image to the specific OCR wrapper inside `backend/app/ocr/`.
   - The wrapper invokes the heavy-lifting OCR code located in `ocr_modules/`.
   - The OCR module extracts text, performs format checks (e.g., Verhoeff checksums for Aadhaar), and returns the parsed data as a dictionary of `fields`.
4. **Module 2 (Database Validation)**:
   - The extracted fields are immediately passed into the `ValidationEngine` (`validator.py`).
   - The `ValidationEngine` queries the actual `SupabaseProvider` using the document's unique identifier (e.g., `aadhaar_number`).
   - The provider fetches the "ground truth" reference record from the `val_*` tables in the Supabase PostgreSQL database.
   - The engine compares the OCR fields against the database record (name fuzzy matching, date normalization, etc.).
5. **Final Result**: The pipeline returns a combined payload containing both the raw OCR result and the Module 2 validation status (`PASS`, `FAIL`, or `WARNING`). The UI updates to show `VERIFIED` or `INCOMPLETE`.

## Project Structure

```
versight_phase_1/
│
├── run.py                          # Master executable script to start the system
├── supabase_migration.sql          # Original migrations + new Module 2 validation tables
├── .env                            # Environment variables (Supabase URL, Key, Postgres URI)
│
├── ocr_modules/                    # Heavy OCR machine learning models and logic (Module 1)
│   ├── aadhar/
│   ├── passport/
│   └── ...
│
└── backend/                        # FastAPI Backend Application (Module 2 + API)
    ├── scripts/
    │   └── setup_db.py             # Script to initialize Supabase and insert 50 synthetic records
    ├── static/
    │   └── index.html              # Frontend testing UI
    └── app/
        ├── main.py                 # FastAPI application definition
        ├── routes/
        │   └── pipeline.py         # The combined OCR -> Validation endpoint
        ├── ocr/
        │   └── *_wrapper.py        # Connectors that import and run code from ocr_modules
        └── module2_validation/     # The validation engine
            └── providers/
                └── supabase_provider.py  # Connects ValidationEngine to actual Supabase DB
```

## Setup & Execution

### 1. Prerequisites
Ensure you have the following installed:
- Python 3.10+
- Required dependencies from `requirements.txt`.
- PostgreSQL driver `psycopg2-binary` (added for the setup script).

### 2. Environment Configuration
Create a `.env` file in the root of `versight_phase_1` (next to `run.py`) and populate it with your Supabase project details:

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-service-role-jwt-key
DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.your-project.supabase.co:5432/postgres
```
*Note: `DATABASE_URL` is required to run the automated table creation and synthetic data insertion script. It uses the direct PostgreSQL connection because the Supabase REST API does not allow creating tables.*

### 3. Running the System
To start the entire system, simply run the master script:

```bash
python run.py
```

**What `run.py` does:**
1. Loads environment variables.
2. Runs `backend/scripts/setup_db.py`. This connects to your Supabase PostgreSQL database, creates the necessary schema (from `supabase_migration.sql` and the `val_*` tables), and automatically inserts 50 synthetic rows for each document type. 
3. Starts the Uvicorn web server hosting the FastAPI application on `http://0.0.0.0:8000`.

### 4. Testing via Browser UI
1. Once the server is running, open your web browser and navigate to:
   **http://localhost:8000/static/index.html**
2. You will see the VeriSight Document Verification UI.
3. Select a document type (e.g., Aadhaar).
4. Upload an image (e.g., from `ocr_modules/aadhar/aadhaar.jpeg`).
5. Click **Run Pipeline**.
6. The system will process the image and display the final matched status (`VERIFIED` or `INCOMPLETE`) against the Supabase database.

## Notes on Synthetic Data

The `setup_db.py` script automatically generates 50 mock entries for each document type (Aadhaar, Passport, Visa, etc.) upon first execution. These entries are inserted into the `val_*` reference tables. 
If an uploaded document's extracted OCR data does not perfectly align with one of these entries, the Module 2 Validation Engine will intelligently fail the document or flag it as `INCOMPLETE` / `WARNING` due to field mismatches.
