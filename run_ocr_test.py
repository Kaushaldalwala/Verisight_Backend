"""
run_ocr_test.py
Runs all 6 document OCR modules against sample images and
writes the full structured API response to response.json
"""

import sys, json, os
sys.path.insert(0, 'backend')

from app.ocr import (
    passport_wrapper,
    aadhaar_wrapper,
    visa_wrapper,
    driving_license_wrapper,
    national_id_wrapper,
    permit_wrapper,
)
from app.ocr.adapter import OCROutputAdapter
from app.module2_validation.services.validation_service import ValidationService

val_service = ValidationService()

test_cases = [
    ('passport',         'ocr_modules/passport/passport.png',               passport_wrapper.process),
    ('aadhaar',          'ocr_modules/aadhar/aadhaar.jpeg',                 aadhaar_wrapper.process),
    ('visa',             'ocr_modules/visa/visa_1.jpg',                     visa_wrapper.process),
    ('driving_license',  'ocr_modules/driving_license/driving_license.jpg', driving_license_wrapper.process),
    ('national_id',      'ocr_modules/national_id/national_id.jpg',         national_id_wrapper.process),
    ('permit',           'ocr_modules/permit/permit.jpg',                   permit_wrapper.process),
]

all_responses = {}

for doc_type, img_path, wrapper_fn in test_cases:
    print(f"[{doc_type.upper()}] Processing {img_path} ...")
    try:
        raw = wrapper_fn(img_path)
        adapted = OCROutputAdapter.adapt(raw, doc_type)
        val = val_service.validate_ocr_output(raw, doc_type)

        all_responses[doc_type] = {
            "document_type":   adapted.get("document_type"),
            "status":          adapted.get("status"),
            "ocr_confidence":  adapted.get("ocr_confidence"),
            "reason":          adapted.get("reason", ""),
            "fields":          adapted.get("fields", {}),
            "validation":      val.model_dump(),
        }
        db_match = val.database_match
        val_status = val.validation_status.value
        print(f"  -> OK  status={adapted.get('status')}  confidence={adapted.get('ocr_confidence')}%  database_match={db_match}  validation={val_status}")
    except Exception as exc:
        all_responses[doc_type] = {"error": str(exc)}
        print(f"  -> ERROR: {exc}")

out_path = os.path.join(os.path.dirname(__file__), "response.json")

# Preserve old results under 'previous_run' key
existing = {}
if os.path.exists(out_path):
    with open(out_path, 'r', encoding='utf-8') as f:
        try:
            existing = json.load(f)
        except Exception:
            existing = {}

# Get previous latest_run or the root-level data as previous
prev_run = existing.get('latest_run', {k: v for k, v in existing.items() if k not in ('previous_run', 'latest_run')})

output = {
    "previous_run": prev_run,
    "latest_run":   all_responses,
}

with open(out_path, "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2, default=str)

print(f"\nAll responses written to: {out_path}")
print("\n=== SUMMARY ===")
for doc_type, res in all_responses.items():
    if 'error' in res:
        print(f"  {doc_type:20s}: ERROR - {res['error']}")
    else:
        val = res.get('validation', {})
        print(f"  {doc_type:20s}: status={res['status'][:20]:20s}  db_match={val.get('database_match')}  validation={val.get('validation_status')}")
