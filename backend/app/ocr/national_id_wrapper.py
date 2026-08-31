"""
national_id.py  (OCR wrapper)

Wraps NationalIDOCR (which extends GenericDocumentOCR)
from ocr_modules/national_id/national_id_ocr.py.
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
from national_id.national_id_ocr import NationalIDOCR  # noqa: E402

# Singleton
_ocr: NationalIDOCR | None = None


def _get_ocr() -> NationalIDOCR:
    global _ocr
    if _ocr is None:
        _ocr = NationalIDOCR(gpu=False)
    return _ocr


def process(image_path: str) -> dict:
    """
    Extract fields from a National ID card using layout-agnostic OCR.

    Returns
    -------
    dict with: document_type, status, ocr_confidence, reason, fields
    """
    ocr = _get_ocr()

    try:
        raw = ocr.process(image_path)
    except (FileNotFoundError, ValueError) as exc:
        return {
            "document_type": "NATIONAL ID",
            "status": "ERROR",
            "ocr_confidence": 0.0,
            "reason": str(exc),
            "fields": {},
        }
    except Exception as exc:
        return {
            "document_type": "NATIONAL ID",
            "status": "ERROR",
            "ocr_confidence": 0.0,
            "reason": f"OCR processing failed: {exc}",
            "fields": {},
        }

    # Flatten field values + include unpaired text for completeness
    flat_fields: dict = {}
    for label, data in (raw.get("fields") or {}).items():
        flat_fields[label] = data.get("value") if isinstance(data, dict) else data

    if raw.get("unpaired_text"):
        flat_fields["_unpaired_text"] = [
            item["text"] for item in raw["unpaired_text"]
        ]

    return {
        "document_type": raw.get("document_type", "NATIONAL ID"),
        "status":        raw.get("status", "UNKNOWN"),
        "ocr_confidence": float(raw.get("ocr_confidence", 0.0)),
        "reason":        raw.get("reason", ""),
        "fields":        flat_fields,
    }
