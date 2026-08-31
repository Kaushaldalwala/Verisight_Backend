"""
commands.py

Command-Line Interface (CLI) runner for Module 2 Document Validation.

Usage:
    python -m backend.app.module2_validation.cli.commands --document passport --id P0000001
"""

import argparse
import json
import sys
from typing import Any

from app.module2_validation.schemas.input import DocumentInput
from app.module2_validation.services.validation_service import ValidationService


def run_cli():
    parser = argparse.ArgumentParser(description="VeriSight Module 2 CLI Document Validator")
    parser.add_argument("--document", type=str, help="Document type (passport, visa, aadhaar, driving_license, national_id, permit)")
    parser.add_argument("--id", type=str, help="Primary document identifier e.g. P0000001")
    parser.add_argument("--validate-json", type=str, help="Raw JSON input payload string")
    args = parser.parse_args()

    service = ValidationService()

    if args.validate_json:
        try:
            payload = json.loads(args.validate_json)
            result = service.validate_direct_input(payload)
        except Exception as exc:
            print(f"Error parsing JSON: {exc}")
            sys.exit(1)
    elif args.document and args.id:
        doc_type = args.document.lower().strip().replace(" ", "_")
        id_field_map = {
            "passport": "passport_number",
            "visa": "visa_number",
            "aadhaar": "aadhaar_number",
            "driving_license": "license_number",
            "national_id": "id_number",
            "permit": "permit_number",
        }
        id_field = id_field_map.get(doc_type, "document_number")

        doc_input = DocumentInput(
            document_type=doc_type,
            fields={id_field: args.id, "name": "DEMO USER"}
        )
        result = service.validator.validate_document(doc_input)
    else:
        # Default test run if no args provided
        doc_input = DocumentInput(
            document_type="passport",
            fields={"passport_number": "P0000001", "name": "ARJUN MEHTA", "date_of_expiry": "2033-04-11"}
        )
        result = service.validator.validate_document(doc_input)

    # Format CLI Output
    print("\n" + "=" * 65)
    print("           VERISIGHT MODULE 2 — VALIDATION RESULT")
    print("=" * 65)
    print(f"Request ID       : {result.request_id}")
    print(f"Document Type    : {result.document_type.upper()}")
    print(f"Data Source      : {result.data_source} ({result.source_status})")
    print(f"Database Match   : {'YES' if result.database_match else 'NO'}")
    print(f"Document Status  : {result.document_status}")
    print(f"Validation Score : {result.validation_score}/100.0")
    print(f"Validation Status: {result.validation_status}")
    print(f"Recommendation   : {result.recommendation}")
    print(f"Processing Time  : {result.processing_time_ms} ms")
    print("=" * 65)

    if result.checks:
        print("\n[ VALIDATION CHECKS ]")
        for check in result.checks:
            mark = "[PASS]" if check.status == "PASS" else "[FAIL]"
            print(f"  {mark:<7} {check.rule:<25} {check.message}")

    if result.mismatches:
        print("\n[ MISMATCHES DETECTED ]")
        for m in result.mismatches:
            print(f"  - Field '{m.field}': {m.message} (OCR: {m.ocr_value} | Ref: {m.reference_value})")

    print("=" * 65 + "\n")


if __name__ == "__main__":
    run_cli()
