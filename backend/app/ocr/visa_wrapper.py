"""
visa.py  (OCR wrapper)

Wraps VisaOCR from ocr_modules/visa/visa_ocr.py.
"""

import sys
from pathlib import Path

# ------------------------------------------------------------------
# Make ocr_modules importable
# ------------------------------------------------------------------
ocr_root = Path(__file__).resolve().parents[3] / "ocr_modules"

if str(ocr_root) not in sys.path:
    sys.path.insert(0, str(ocr_root))

# pyrefly: ignore [missing-import]
from visa.visa_ocr import VisaOCR  # noqa: E402

# Singleton
_ocr: VisaOCR | None = None


def _get_ocr() -> VisaOCR:
    global _ocr
    if _ocr is None:
        _ocr = VisaOCR(gpu=False)
    return _ocr


def process(image_path: str) -> dict:
    """
    Extract and cross-validate visa fields from the given image.

    Returns
    -------
    dict with: document_type, status, ocr_confidence, reason, fields
    """
    ocr = _get_ocr()

    try:
        raw = ocr.process(image_path)
    except Exception as exc:
        return {
            "document_type": "VISA",
            "status": "ERROR",
            "ocr_confidence": 0.0,
            "reason": str(exc),
            "fields": {},
        }

    confidence = float(raw.get("ocr_confidence", 0.0))

    # Build fields dict — include extracted fields + MRZ + checks
    fields: dict = {}

    if raw.get("fields"):
        fields["extracted"] = raw["fields"]

    if raw.get("mrz"):
        fields["mrz"] = raw["mrz"]

    if raw.get("checks"):
        fields["checks"] = raw["checks"]

    if raw.get("matches") is not None:
        fields["matches"]       = raw["matches"]
        fields["close_matches"] = raw.get("close_matches", 0)
        fields["mismatches"]    = raw.get("mismatches", 0)

    return {
        "document_type": raw.get("document_type", "VISA"),
        "status":        raw.get("status", "UNKNOWN"),
        "ocr_confidence": confidence,
        "reason":        raw.get("reason", ""),
        "fields":        fields,
    }
