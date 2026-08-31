"""
aadhaar.py  (OCR wrapper)

Wraps AadhaarOCR from ocr_modules/aadhar/aadhaar_ocr.py.

Sets the Tesseract path before import so the optional fallback works.
"""

import os
import sys
from pathlib import Path

# ------------------------------------------------------------------
# Set Tesseract path (Windows) before importing pytesseract
# ------------------------------------------------------------------
TESSERACT_CMD = os.getenv(
    "TESSERACT_CMD",
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
)

try:
    import pytesseract
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
except ImportError:
    pass  # Tesseract is optional — EasyOCR handles the primary extraction

# ------------------------------------------------------------------
# Make ocr_modules importable
# ------------------------------------------------------------------
_OCR_MODULES_ROOT = Path(__file__).resolve().parents[3] / "ocr_modules"
if str(_OCR_MODULES_ROOT) not in sys.path:
    sys.path.insert(0, str(_OCR_MODULES_ROOT))

# pyrefly: ignore [missing-import]
from aadhar.aadhaar_ocr import AadhaarOCR  # noqa: E402

# Singleton
_ocr: AadhaarOCR | None = None


def _get_ocr() -> AadhaarOCR:
    global _ocr
    if _ocr is None:
        _ocr = AadhaarOCR(gpu=False)
    return _ocr


def process(image_path: str) -> dict:
    """
    Extract and validate Aadhaar number from the given image file.

    Returns
    -------
    dict with: document_type, status, ocr_confidence, reason, fields
    """
    ocr = _get_ocr()

    try:
        raw = ocr.process(image_path)
    except Exception as exc:
        return {
            "document_type": "AADHAAR",
            "status": "ERROR",
            "ocr_confidence": 0.0,
            "reason": str(exc),
            "fields": {},
        }

    # Flatten the raw result into our standard shape
    confidence = float(raw.get("ocr_confidence", 0.0))

    fields = {
        k: v
        for k, v in raw.items()
        if k not in ("document_type", "status", "ocr_confidence", "reason")
    }

    return {
        "document_type": raw.get("document_type", "AADHAAR"),
        "status":        raw.get("status", "UNKNOWN"),
        "ocr_confidence": confidence,
        "reason":        raw.get("reason", ""),
        "fields":        fields,
    }
