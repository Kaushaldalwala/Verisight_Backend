"""
permit.py  (OCR wrapper)

Wraps PermitOCR (which extends GenericDocumentOCR)
from ocr_modules/permit/permit_ocr.py.
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
from permit.permit_ocr import PermitOCR  # noqa: E402

# Singleton
_ocr: PermitOCR | None = None


def _get_ocr() -> PermitOCR:
    global _ocr
    if _ocr is None:
        _ocr = PermitOCR(gpu=False)
    return _ocr


def process(image_path: str) -> dict:
    """
    Extract fields from a permit/pass document using layout-agnostic OCR.

    Returns
    -------
    dict with: document_type, status, ocr_confidence, reason, fields
    """
    ocr = _get_ocr()

    try:
        raw = ocr.process(image_path)
    except (FileNotFoundError, ValueError) as exc:
        return {
            "document_type": "PERMIT",
            "status": "ERROR",
            "ocr_confidence": 0.0,
            "reason": str(exc),
            "fields": {},
        }
    except Exception as exc:
        return {
            "document_type": "PERMIT",
            "status": "ERROR",
            "ocr_confidence": 0.0,
            "reason": f"OCR processing failed: {exc}",
            "fields": {},
        }

    flat_fields: dict = {}
    for label, data in (raw.get("fields") or {}).items():
        flat_fields[label] = data.get("value") if isinstance(data, dict) else data

    if raw.get("unpaired_text"):
        flat_fields["_unpaired_text"] = [
            item["text"] for item in raw["unpaired_text"]
        ]

    return {
        "document_type": raw.get("document_type", "PERMIT"),
        "status":        raw.get("status", "UNKNOWN"),
        "ocr_confidence": float(raw.get("ocr_confidence", 0.0)),
        "reason":        raw.get("reason", ""),
        "fields":        flat_fields,
    }
