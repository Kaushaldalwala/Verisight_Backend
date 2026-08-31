"""
scan_logger.py

Persists every OCR scan result to the scan_logs table in Supabase.

The admin client is used so that RLS does not block the insert —
the JWT of the requesting officer is stored as officer_id for audit purposes.
"""

import logging
import time
from typing import Any

from app.services.supabase import supabase_admin

logger = logging.getLogger(__name__)


def log_scan(
    officer_id: str,
    document_type: str,
    status: str,
    fields: dict[str, Any],
    ocr_confidence: float = 0.0,
    image_filename: str | None = None,
    image_path: str | None = None,
    processing_ms: int | None = None,
) -> dict[str, Any]:
    """
    Insert a scan log row into the scan_logs table.

    Parameters
    ----------
    officer_id      : UUID string of the authenticated officer
    document_type   : one of passport | aadhaar | visa | driving_license |
                      national_id | permit
    status          : the status string returned by the OCR module
    fields          : all extracted fields (dict, stored as JSONB)
    ocr_confidence  : float 0–100
    image_filename  : original uploaded filename (optional)
    image_path      : path to stored image in Supabase storage (optional)
    processing_ms   : processing time in milliseconds (optional)

    Returns
    -------
    Inserted row data dict (or empty dict on error)
    """
    try:
        # 1. Adapt and normalize fields using OCROutputAdapter to get structured results
        doc_type_clean = document_type.lower().strip().replace(" ", "_")
        try:
            from app.ocr.adapter import OCROutputAdapter
            raw_ocr = {
                "document_type": document_type,
                "status": status,
                "ocr_confidence": ocr_confidence,
                "fields": fields
            }
            adapted = OCROutputAdapter.adapt(raw_ocr, doc_type_clean)
            normalized_fields = adapted.get("fields", {})
            if adapted.get("document_country"):
                normalized_fields["country"] = adapted["document_country"]
        except Exception as adapt_exc:
            logger.warning("[scan_logger] Could not adapt raw OCR result: %s", adapt_exc)
            normalized_fields = fields

        # 2. Insert into the main scan_logs table
        payload = {
            "officer_id":     officer_id,
            "document_type":  document_type,
            "status":         status,
            "ocr_confidence": round(ocr_confidence, 2),
            "fields":         fields,
        }

        if image_filename:
            payload["image_filename"] = image_filename

        if image_path:
            payload["image_path"] = image_path

        if processing_ms is not None:
            payload["processing_ms"] = processing_ms

        response = (
            supabase_admin
            .table("scan_logs")
            .insert(payload)
            .execute()
        )

        log_row = response.data[0] if response.data else {}

        # 3. Insert structured data into the document-specific table
        DOC_TABLE_MAP = {
            "passport": "ocr_passports",
            "aadhaar": "ocr_aadhaars",
            "visa": "ocr_visas",
            "driving_license": "ocr_driving_licenses",
            "national_id": "ocr_national_ids",
            "permit": "ocr_permits",
        }

        SCHEMA_COLS = {
            "passport": [
                "passport_number", "name", "surname", "given_name",
                "nationality", "date_of_birth", "date_of_issue", "date_of_expiry",
                "gender", "personal_number", "passport_type",
                "place_of_birth", "issuing_authority",
                "mrz_line1", "mrz_line2", "country",
            ],
            "aadhaar": [
                "aadhaar_number", "masked_number", "name",
                "gender", "date_of_birth", "address", "country",
            ],
            "visa": [
                "visa_number", "control_number", "visa_type", "entries",
                "issuing_post", "issuing_authority", "annotation",
                "name", "surname", "given_name",
                "date_of_birth", "passport_number", "nationality",
                "date_of_issue", "date_of_expiry",
                "mrz_line1", "mrz_line2", "country",
            ],
            "driving_license": [
                "license_number", "name",
                "date_of_issue", "date_of_expiry", "date_of_birth",
                "blood_group", "relation", "address",
                "vehicle_classes", "issuing_authority", "nationality", "country",
            ],
            "national_id": [
                "id_number", "name", "surname", "given_name",
                "nationality", "date_of_birth", "date_of_issue", "date_of_expiry",
                "gender", "place_of_birth", "address",
                "issuing_authority", "mrz_line1", "mrz_line2", "country",
            ],
            "permit": [
                "permit_number", "permit_type",
                "name", "surname", "given_name",
                "date_of_birth", "date_of_issue", "date_of_expiry",
                "gender", "nationality", "passport_number",
                "issuing_authority", "address",
                "mrz_line1", "mrz_line2", "country",
            ],
        }

        if log_row and doc_type_clean in DOC_TABLE_MAP:
            table_name = DOC_TABLE_MAP[doc_type_clean]
            columns = SCHEMA_COLS.get(doc_type_clean, [])
            
            child_payload = {
                "scan_log_id": log_row.get("id"),
                "officer_id": officer_id,
            }
            
            for col in columns:
                if col in normalized_fields:
                    child_payload[col] = normalized_fields[col]
            
            try:
                supabase_admin.table(table_name).insert(child_payload).execute()
            except Exception as child_exc:
                logger.warning("[scan_logger] Could not insert into structured table %s: %s", table_name, child_exc)

        return log_row

    except Exception as exc:
        # Never let a logging failure break the OCR response
        logger.warning("[scan_logger] Could not log scan: %s", exc)
        return {}
