"""
test_insert.py — Login, hit all OCR endpoints, verify scan_log_id (= DB insert).
Run: python test_insert.py
"""

import sys
import requests

BASE = "http://127.0.0.1:8000"
TINY_JPEG = (
    b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t"
    b"\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a"
    b"\x1f\x1e\x1d\x1a\x1c\x1c $.' \",#\x1c\x1c(7),01444\x1f'9=82<.342\x1e\x1b"
    b"\x1f\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4"
    b"\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00"
    b"\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xc4"
    b"\x00\xb5\x10\x00\x02\x01\x03\x03\x02\x04\x03\x05\x05\x04\x04\x00"
    b"\x00\x01}\x01\x02\x03\x00\x04\x11\x05\x12!1A\x06\x13Qa\x07\"q\x142"
    b"\x81\x91\xa1\x08#B\xb1\xc1\x15R\xd1\xf0$3br\x82\t\n\x16\x17\x18"
    b"\x19\x1a%&'()*456789:CDEFGHIJSTUVWXYZcdefghijstuvwxyz\x83\x84\x85"
    b"\x86\x87\x88\x89\x8a\x92\x93\x94\x95\x96\x97\x98\x99\x9a\xa2\xa3"
    b"\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba"
    b"\xc2\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca\xd2\xd3\xd4\xd5\xd6\xd7\xd8"
    b"\xd9\xda\xe1\xe2\xe3\xe4\xe5\xe6\xe7\xe8\xe9\xea\xf1\xf2\xf3\xf4"
    b"\xf5\xf6\xf7\xf8\xf9\xfa\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xfb"
    b"\xd4P\x00\x00\x00\x1f\xff\xd9"
)

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"
BOLD = "\033[1m"


def main() -> int:
    print(f"\n{BOLD}=== VeriSight API Insert Test ==={RESET}\n")

    # Health
    r = requests.get(f"{BASE}/", timeout=10)
    print(f"[1] GET / -> {r.status_code} {r.json()}")

    r = requests.get(f"{BASE}/test-supabase", timeout=15)
    print(f"[2] GET /test-supabase -> {r.status_code} {r.json()}")

    # Login
    creds = {"officer_email": "doctest@verisight.dev", "password": "Test@1234567"}
    r = requests.post(f"{BASE}/auth/login", json=creds, timeout=15)
    print(f"[3] POST /auth/login -> {r.status_code}")
    if r.status_code != 200:
        print(f"    {RED}FAIL:{RESET} {r.text}")
        return 1

    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print(f"    {GREEN}token received{RESET}")

    # Profile
    r = requests.get(f"{BASE}/auth/me", headers=headers, timeout=15)
    print(f"[4] GET /auth/me -> {r.status_code}")
    if r.status_code == 200:
        p = r.json()
        print(f"    officer: {p.get('officer_id')} | {p.get('first_name')} {p.get('last_name')}")

    # OCR — scan_log_id proves row was inserted into scan_logs
    endpoints = [
        ("/ocr/passport", "passport"),
        ("/ocr/aadhaar", "aadhaar"),
        ("/ocr/visa", "visa"),
        ("/ocr/driving-license", "driving_license"),
        ("/ocr/national-id", "national_id"),
        ("/ocr/permit", "permit"),
    ]

    inserted = []
    print(f"\n{BOLD}[5] OCR endpoints (checking DB insert via scan_log_id){RESET}")
    for path, dtype in endpoints:
        r = requests.post(
            f"{BASE}{path}",
            headers=headers,
            files={"file": ("test.jpg", TINY_JPEG, "image/jpeg")},
            timeout=180,
        )
        if r.status_code != 200:
            print(f"  {RED}[FAIL]{RESET} POST {path} -> {r.status_code} {r.text[:150]}")
            continue

        body = r.json()
        log_id = body.get("scan_log_id")
        if log_id:
            inserted.append(
                {
                    "document_type": dtype,
                    "scan_log_id": log_id,
                    "status": body.get("status"),
                    "confidence": body.get("ocr_confidence"),
                }
            )
            print(
                f"  {GREEN}[PASS]{RESET} POST {path} -> "
                f"scan_log_id={log_id} status={body.get('status')} "
                f"confidence={body.get('ocr_confidence')}"
            )
        else:
            print(
                f"  {RED}[FAIL]{RESET} POST {path} -> 200 but no scan_log_id "
                f"(insert may have failed)"
            )

    print(f"\n{BOLD}=== INSERT SUMMARY ==={RESET}")
    print(f"OCR calls: {len(endpoints)}")
    print(f"Rows inserted: {len(inserted)}/{len(endpoints)}")
    for row in inserted:
        print(f"  • {row['document_type']}: {row['scan_log_id']} [{row['status']}]")

    if len(inserted) == len(endpoints):
        print(f"\n{GREEN}{BOLD}ALL DATA INSERTED into scan_logs ✓{RESET}\n")
        return 0

    print(f"\n{YELLOW}Some inserts missing — check server logs for [scan_logger] warnings{RESET}\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())
