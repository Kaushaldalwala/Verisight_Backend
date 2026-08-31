"""
test_real_docs.py — Full API test with real document images + signup/login.
Run: python test_real_docs.py
"""

import json
import sys
import time
from pathlib import Path

import requests

BASE = "http://127.0.0.1:8000"

IMAGES = {
    "/ocr/aadhaar":          r"D:\hackathons\SIH-2026\OCR\ocr_modules\aadhar\aadhaar.jpeg",
    "/ocr/passport":         r"D:\hackathons\SIH-2026\OCR\passport_ocr\images\passport_1.png",
    "/ocr/visa":             r"D:\hackathons\SIH-2026\OCR\ocr_modules\visa\visa_1.jpg",
    "/ocr/driving-license":  r"D:\hackathons\SIH-2026\OCR\ocr_modules\driving_license\driving_license.jpg",
    "/ocr/national-id":      r"D:\hackathons\SIH-2026\OCR\ocr_modules\national_id\national_id.jpg",
    "/ocr/permit":           r"D:\hackathons\SIH-2026\OCR\ocr_modules\permit\permit.jpg",
}

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"
BOLD = "\033[1m"

ts = int(time.time())
OFFICER = {
    "first_name":    "Real",
    "last_name":     "DocTester",
    "officer_id":    f"OFF-REAL-{ts}",
    "officer_email": f"realtest_{ts}@verisight.dev",
    "password":      "Test@1234567",
    "organization":  "VeriSight QA",
    "designation":   "Inspector",
}

results = []


def section(title: str) -> None:
    print(f"\n{BOLD}{CYAN}{'─' * 55}{RESET}")
    print(f"{BOLD}{CYAN}  {title}{RESET}")
    print(f"{BOLD}{CYAN}{'─' * 55}{RESET}")


def record(label: str, ok: bool, detail: str = "") -> None:
    mark = f"{GREEN}[PASS]{RESET}" if ok else f"{RED}[FAIL]{RESET}"
    print(f"  {mark} {label}")
    if detail:
        print(f"         {YELLOW}{detail[:300]}{RESET}")
    results.append(ok)


def mime_for(path: Path) -> str:
    ext = path.suffix.lower()
    return {
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".png": "image/png", ".webp": "image/webp",
    }.get(ext, "image/jpeg")


def main() -> int:
    print(f"\n{BOLD}=== VeriSight Real Document API Test ==={RESET}")
    print(f"Base: {BASE}\n")

    access_token = None
    login_email = OFFICER["officer_email"]
    login_password = OFFICER["password"]

    # ── SIGNUP ──
    section("1. POST /auth/signup")
    try:
        r = requests.post(f"{BASE}/auth/signup", json=OFFICER, timeout=30)
        ok = r.status_code == 200
        record("Signup new officer", ok, f"[{r.status_code}] {r.text[:250]}")
        if ok:
            print(f"         {GREEN}Created: {OFFICER['officer_email']}{RESET}")
        elif r.status_code == 429 or "rate limit" in r.text.lower():
            print(f"         {YELLOW}Rate limited — will use existing test account for login{RESET}")
            login_email = "doctest@verisight.dev"
            login_password = "Test@1234567"
        else:
            login_email = "doctest@verisight.dev"
            login_password = "Test@1234567"
    except Exception as e:
        record("Signup", False, str(e))
        login_email = "doctest@verisight.dev"
        login_password = "Test@1234567"

    # ── LOGIN ──
    section("2. POST /auth/login")
    try:
        r = requests.post(
            f"{BASE}/auth/login",
            json={"officer_email": login_email, "password": login_password},
            timeout=15,
        )
        ok = r.status_code == 200
        record(f"Login as {login_email}", ok, f"[{r.status_code}] {r.text[:200]}")
        if ok:
            access_token = r.json()["access_token"]
            print(f"         {GREEN}token: {access_token[:50]}...{RESET}")
    except Exception as e:
        record("Login", False, str(e))

    if not access_token:
        print(f"\n{RED}Cannot continue without token.{RESET}\n")
        return 1

    headers = {"Authorization": f"Bearer {access_token}"}

    # ── /me ──
    section("3. GET /auth/me")
    try:
        r = requests.get(f"{BASE}/auth/me", headers=headers, timeout=15)
        ok = r.status_code == 200
        record("Get profile", ok, f"[{r.status_code}]")
        if ok:
            p = r.json()
            print(f"         {GREEN}{p.get('first_name')} {p.get('last_name')} | {p.get('officer_id')} | {p.get('organization')}{RESET}")
    except Exception as e:
        record("/auth/me", False, str(e))

    # ── OCR with real images ──
    section("4. OCR Endpoints (real document images)")
    for path, img_path in IMAGES.items():
        p = Path(img_path)
        label = path.replace("/ocr/", "").upper()
        if not p.exists():
            record(f"{label} — file missing", False, img_path)
            continue

        mime = mime_for(p)
        try:
            with open(p, "rb") as f:
                r = requests.post(
                    f"{BASE}{path}",
                    headers=headers,
                    files={"file": (p.name, f, mime)},
                    timeout=600,
                )
            ok = r.status_code == 200
            if ok:
                d = r.json()
                log_id = d.get("scan_log_id")
                fields = d.get("fields") or {}
                field_preview = json.dumps(fields, ensure_ascii=False)[:200]
                record(
                    f"{label:<20} [{d.get('status')}] conf={d.get('ocr_confidence')}",
                    log_id is not None,
                    f"scan_log_id={log_id} | fields={field_preview}",
                )
            else:
                record(f"{label}", False, f"[{r.status_code}] {r.text[:200]}")
        except Exception as e:
            record(f"{label}", False, str(e))

    # ── Summary ──
    passed = sum(results)
    total = len(results)
    color = GREEN if passed == total else YELLOW
    print(f"\n{BOLD}{'═' * 55}{RESET}")
    print(f"  {color}{BOLD}{passed}/{total} checks passed{RESET}")
    print(f"{BOLD}{'═' * 55}{RESET}\n")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
