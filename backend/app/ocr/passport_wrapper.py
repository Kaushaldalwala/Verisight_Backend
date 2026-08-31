"""
passport.py  (OCR wrapper)

Wraps PassportOCR from ocr_modules/passport/passport_ocr.py.

The reader is initialized once (singleton) and reused across requests.
"""

import sys
from pathlib import Path

# ------------------------------------------------------------------
# Make ocr_modules importable from this backend
# ------------------------------------------------------------------
_OCR_MODULES_ROOT = Path(__file__).resolve().parents[3] / "ocr_modules"
if str(_OCR_MODULES_ROOT) not in sys.path:
    sys.path.insert(0, str(_OCR_MODULES_ROOT))

# pyrefly: ignore [missing-import]
from passport.passport_ocr import PassportOCR  # noqa: E402

# Singleton — loaded once per server process
_ocr: PassportOCR | None = None


def _get_ocr() -> PassportOCR:
    global _ocr
    if _ocr is None:
        _ocr = PassportOCR(gpu=False)
    return _ocr


def process(image_path: str) -> dict:
    """
    Extract passport data from the given image file.

    Parameters
    ----------
    image_path : str
        Absolute path to the uploaded passport image.

    Returns
    -------
    dict with keys: document_type, status, ocr_confidence, reason, fields
    """
    ocr = _get_ocr()

    try:
        raw = ocr.get_data(image_path)
    except Exception as exc:
        return {
            "document_type": "PASSPORT",
            "status": "ERROR",
            "ocr_confidence": 0.0,
            "reason": str(exc),
            "fields": {},
        }

    if not raw:
        return {
            "document_type": "PASSPORT",
            "status": "CLEARER IMAGE REQUIRED",
            "ocr_confidence": 0.0,
            "reason": "The MRZ could not be read from this image.",
            "fields": {},
        }

    return {
        "document_type": "PASSPORT",
        "status": "OCR SUCCESS",
        "ocr_confidence": 100.0,   # PassportOCR does not expose a confidence score
        "reason": "Passport MRZ extracted successfully.",
        "fields": raw,
    }
