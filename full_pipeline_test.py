"""
full_pipeline_test.py — Full Integrated Pipeline Test for VeriSight

Flow:
Document Image / Raw OCR Output → Module 1 Wrapper → Normalization Adapter → Module 2 Validation Engine → Integrated OCRResponse
"""

import sys
import os
import json
import logging
from pathlib import Path

# Add backend to sys.path
backend_path = Path(__file__).resolve().parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from app.ocr.adapter import OCROutputAdapter
from app.module2_validation.database.repository import DocumentRepository
from app.module2_validation.services.validation_service import ValidationService
from app.module2_validation.schemas.common import ValidationStatus

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("full_pipeline_test")


def run_full_pipeline_test():
    print("\n" + "=" * 75)
    print("      VERISIGHT FULL INTEGRATED PIPELINE TEST (MODULE 1 + MODULE 2)")
    print("=" * 75)

    val_service = ValidationService()
    repo = DocumentRepository()
    results = []

    # Document types to test
    test_specs = [
        ("passport", "P0000001", "passport_number"),
        ("visa", "V00000001", "visa_number"),
        ("aadhaar", "000000000001", "aadhaar_number"),
        ("driving_license", "DL0000000001", "license_number"),
        ("national_id", "NID00000001", "id_number"),
        ("permit", "PER00000001", "permit_number"),
    ]

    for doc_type, identifier, id_field in test_specs:
        rec = repo.find_by_identifier(doc_type, identifier)
        if not rec:
            print(f"Skipping {doc_type}: record {identifier} not found in database")
            continue

        # Force record status to ACTIVE for clear PASS test
        rec["status"] = "ACTIVE"

        # Simulate Module 1 OCR output
        raw_ocr = {
            "document_type": doc_type.upper(),
            "status": "OCR SUCCESS",
            "ocr_confidence": 96.0,
            "reason": f"Extracted {doc_type} text successfully.",
            "fields": rec
        }

        print(f"\n--- Testing Document Type: {doc_type.upper()} ({identifier}) ---")

        # Step 1: Module 1 -> Normalization Adapter
        adapted = OCROutputAdapter.adapt(raw_ocr, doc_type)
        print(f"  [Module 1 Adapter] Normalized Fields: {list(adapted['fields'].keys())}")

        # Step 2: Normalization Adapter -> Module 2 Validation Engine
        result = val_service.validate_ocr_output(raw_ocr, doc_type)

        print(f"  [Module 2 Engine ] Status         : {result.validation_status}")
        print(f"  [Module 2 Engine ] Score          : {result.validation_score}/100.0")
        print(f"  [Module 2 Engine ] Database Match : {'YES' if result.database_match else 'NO'}")
        print(f"  [Module 2 Engine ] Data Source    : {result.data_source}")
        print(f"  [Module 2 Engine ] Doc Status     : {result.document_status}")

        if result.mismatches:
            print(f"  [Module 2 Engine ] Mismatches     : {[m.message for m in result.mismatches]}")

        is_pass = result.validation_status in (ValidationStatus.PASS, ValidationStatus.MANUAL_REVIEW)
        results.append(is_pass)

    print("\n" + "=" * 75)
    passed_count = sum(1 for r in results if r)
    total_count = len(results)
    print(f"  SUMMARY: {passed_count}/{total_count} integrated document pipeline tests passed!")
    print("=" * 75 + "\n")
    return passed_count == total_count


if __name__ == "__main__":
    success = run_full_pipeline_test()
    sys.exit(0 if success else 1)
