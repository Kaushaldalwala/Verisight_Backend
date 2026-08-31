"""
routes/ocr.py

OCR endpoints for VeriSight.  The user explicitly selects the document type;
there is no auto-detection.

All endpoints:
  - Require a valid Bearer token (officer must be authenticated)
  - Accept a single image file (JPEG / PNG / WEBP / BMP)
  - Run the appropriate OCR module
  - Log the result to Supabase scan_logs
  - Return a unified OCRResponse

Endpoints:
  POST /ocr/passport
  POST /ocr/aadhaar
  POST /ocr/visa
  POST /ocr/driving-license
  POST /ocr/national-id
  POST /ocr/permit
"""

import os
import time
import tempfile
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status

from app.dependencies.auth import get_current_user
from app.services.supabase import supabase_admin
from app.services.scan_logger import log_scan
from app.schemas.ocr import OCRResponse
from app.module2_validation.services.validation_service import ValidationService
from app.ocr.adapter import OCROutputAdapter

# OCR wrappers (lazy imports inside each endpoint so models load only when used)
import app.ocr.passport_wrapper        as _passport_ocr
import app.ocr.aadhaar_wrapper         as _aadhaar_ocr
import app.ocr.visa_wrapper            as _visa_ocr
import app.ocr.driving_license_wrapper as _dl_ocr
import app.ocr.national_id_wrapper     as _nid_ocr
import app.ocr.permit_wrapper          as _permit_ocr

router = APIRouter()
logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Allowed image MIME types
# ------------------------------------------------------------------
ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "image/bmp",
    "image/tiff",
}

# Maximum upload size: 10 MB
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024


# ------------------------------------------------------------------
# Helper: save upload to temp file, run OCR, clean up
# ------------------------------------------------------------------
def _run_ocr(
    upload: UploadFile,
    processor_fn,
    current_user,
    doc_type: str,
) -> OCRResponse:

    # Validate content type
    if upload.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                f"Unsupported file type '{upload.content_type}'. "
                f"Allowed types: JPEG, PNG, WEBP, BMP, TIFF."
            ),
        )

    # Read file bytes
    file_bytes = upload.file.read()

    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File too large. Maximum allowed size is 10 MB.",
        )

    if len(file_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty file uploaded.",
        )

    # Determine extension from MIME type
    ext_map = {
        "image/jpeg": ".jpg",
        "image/jpg":  ".jpg",
        "image/png":  ".png",
        "image/webp": ".webp",
        "image/bmp":  ".bmp",
        "image/tiff": ".tiff",
    }
    suffix = ext_map.get(upload.content_type, ".jpg")

    # Upload to Supabase Storage first
    image_path = None
    try:
        timestamp = int(time.time())
        # Safe filename to prevent path injection / issues in URL
        safe_name = "".join(c for c in upload.filename if c.isalnum() or c in "._-")
        image_path = f"{current_user.id}/{timestamp}_{safe_name}"
        
        supabase_admin.storage.from_("scanned-documents").upload(
            path=image_path,
            file=file_bytes,
            file_options={"content-type": upload.content_type}
        )
    except Exception as exc:
        logger.warning("[Storage] Could not upload scanned document to storage: %s", exc)
        image_path = None

    # Write to temp file for local OCR module to read
    tmp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            suffix=suffix,
            delete=False,
        ) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        # Run OCR and measure time
        start_ms = time.monotonic()
        raw_result = processor_fn(tmp_path)
        elapsed_ms = int((time.monotonic() - start_ms) * 1000)

    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass

    # Adapt raw OCR result into standard, generalized structured fields
    adapted = OCROutputAdapter.adapt(raw_result, doc_type_override=doc_type)

    # Log to Supabase
    log_row = log_scan(
        officer_id=current_user.id,
        document_type=adapted["document_type"],
        status=adapted["status"],
        fields=adapted["fields"],
        ocr_confidence=adapted["ocr_confidence"],
        image_filename=upload.filename,
        image_path=image_path,
        processing_ms=elapsed_ms,
    )

    # Run Module 2 Validation on the extracted OCR result
    val_result = None
    try:
        val_service = ValidationService()
        val_result = val_service.validate_ocr_output(raw_result, doc_type)
    except Exception as exc:
        logger.warning("[Validation] Could not run Module 2 validation: %s", exc)

    return OCRResponse(
        document_type  = adapted.get("document_type", doc_type),
        status         = adapted.get("status", "UNKNOWN"),
        ocr_confidence = adapted.get("ocr_confidence", 0.0),
        reason         = adapted.get("reason", ""),
        fields         = adapted.get("fields", {}),
        scan_log_id    = log_row.get("id") if log_row else None,
        validation     = val_result,
    )


# ------------------------------------------------------------------
# POST /ocr/passport
# ------------------------------------------------------------------
@router.post(
    "/passport",
    response_model=OCRResponse,
    summary="Extract data from a Passport (MRZ-based OCR)",
)
async def ocr_passport(
    file: UploadFile = File(..., description="Passport image (JPEG/PNG/WEBP)"),
    current_user=Depends(get_current_user),
):
    """
    Upload a passport image. The API reads the Machine Readable Zone (MRZ)
    and returns structured data: name, date of birth, passport number,
    nationality, issuing country, expiry date, etc.
    """
    return _run_ocr(file, _passport_ocr.process, current_user, "passport")


# ------------------------------------------------------------------
# POST /ocr/aadhaar
# ------------------------------------------------------------------
@router.post(
    "/aadhaar",
    response_model=OCRResponse,
    summary="Extract and validate an Aadhaar card number",
)
async def ocr_aadhaar(
    file: UploadFile = File(..., description="Aadhaar card image (JPEG/PNG/WEBP)"),
    current_user=Depends(get_current_user),
):
    """
    Upload an Aadhaar card image. The API extracts the 12-digit Aadhaar number,
    runs Verhoeff checksum validation, and returns a masked version plus
    OCR confidence metrics.
    """
    return _run_ocr(file, _aadhaar_ocr.process, current_user, "aadhaar")


# ------------------------------------------------------------------
# POST /ocr/visa
# ------------------------------------------------------------------
@router.post(
    "/visa",
    response_model=OCRResponse,
    summary="Extract and cross-validate a Visa document",
)
async def ocr_visa(
    file: UploadFile = File(..., description="Visa image (JPEG/PNG/WEBP)"),
    current_user=Depends(get_current_user),
):
    """
    Upload a visa image. The API extracts visible fields (name, passport number,
    nationality, dates, visa type, etc.) and cross-validates them against the
    Machine Readable Zone (MRZ) found in the lower portion of the document.
    """
    return _run_ocr(file, _visa_ocr.process, current_user, "visa")


# ------------------------------------------------------------------
# POST /ocr/driving-license
# ------------------------------------------------------------------
@router.post(
    "/driving-license",
    response_model=OCRResponse,
    summary="Extract fields from an Indian Driving Licence",
)
async def ocr_driving_license(
    file: UploadFile = File(..., description="Driving licence image (JPEG/PNG/WEBP)"),
    current_user=Depends(get_current_user),
):
    """
    Upload an Indian driving licence image. The API uses region-based OCR
    to extract: licence number, date of issue, validity, date of birth,
    blood group, name, and relation.
    """
    return _run_ocr(file, _dl_ocr.process, current_user, "driving_license")


# ------------------------------------------------------------------
# POST /ocr/national-id
# ------------------------------------------------------------------
@router.post(
    "/national-id",
    response_model=OCRResponse,
    summary="Extract fields from a National ID card (layout-agnostic)",
)
async def ocr_national_id(
    file: UploadFile = File(..., description="National ID image (JPEG/PNG/WEBP)"),
    current_user=Depends(get_current_user),
):
    """
    Upload a National ID card image. The API uses layout-agnostic OCR —
    it detects key/value relationships without a fixed template, making it
    work across different countries and card formats.
    """
    return _run_ocr(file, _nid_ocr.process, current_user, "national_id")


# ------------------------------------------------------------------
# POST /ocr/permit
# ------------------------------------------------------------------
@router.post(
    "/permit",
    response_model=OCRResponse,
    summary="Extract fields from a Permit / Pass document (layout-agnostic)",
)
async def ocr_permit(
    file: UploadFile = File(..., description="Permit/pass image (JPEG/PNG/WEBP)"),
    current_user=Depends(get_current_user),
):
    """
    Upload a permit or pass image. Uses the same layout-agnostic OCR as
    National ID — suitable for work permits, entry passes, and similar documents.
    """
    return _run_ocr(file, _permit_ocr.process, current_user, "permit")
