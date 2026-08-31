"""
driving_license.py  (OCR wrapper)

Wraps DrivingLicenseOCR from ocr_modules/driving_license/driving_license_ocr.py.
"""

import sys
from pathlib import Path

# ------------------------------------------------------------------
# Make ocr_modules importable
# ------------------------------------------------------------------
_OCR_MODULES_ROOT = Path(__file__).resolve().parents[3] / "ocr_modules"
if str(_OCR_MODULES_ROOT) not in sys.path:
    sys.path.insert(0, str(_OCR_MODULES_ROOT))

# pyrefly: ignore [missing-import]
from driving_license.driving_license_ocr import DrivingLicenseOCR  # noqa: E402

# Singleton
_ocr: DrivingLicenseOCR | None = None


def _get_ocr() -> DrivingLicenseOCR:
    global _ocr
    if _ocr is None:
        _ocr = DrivingLicenseOCR(gpu=False)
    return _ocr


def process(image_path: str) -> dict:
    """
    Extract Indian driving licence fields from the given image.

    Returns
    -------
    dict with: document_type, status, ocr_confidence, reason, fields
    """
    ocr = _get_ocr()

    try:
        raw = ocr.process(image_path)
    except Exception as exc:
        return {
            "document_type": "DRIVING LICENSE",
            "status": "ERROR",
            "ocr_confidence": 0.0,
            "reason": str(exc),
            "fields": {},
        }

    # Flatten field values for easy API consumption
    flat_fields: dict = {}
    for key, data in (raw.get("fields") or {}).items():
        flat_fields[key] = data.get("value") if isinstance(data, dict) else data

    return {
        "document_type": raw.get("document_type", "DRIVING LICENSE"),
        "status":        raw.get("status", "UNKNOWN"),
        "ocr_confidence": float(raw.get("ocr_confidence", 0.0)),
        "reason":        raw.get("reason", ""),
        "fields":        flat_fields,
    }
