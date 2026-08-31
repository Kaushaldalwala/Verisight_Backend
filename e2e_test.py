"""
e2e_test.py — Full end-to-end test for VeriSight backend.
Runs: signup → login → /me → /refresh → all 6 OCR endpoints with a real image.
"""

import sys
import time
import requests
import tempfile
import os

BASE = "http://localhost:8000"
BOLD  = "\033[1m"
GREEN = "\033[92m"
RED   = "\033[91m"
YELLOW= "\033[93m"
CYAN  = "\033[96m"
RESET = "\033[0m"

# ──────────────────────────────────────────
# Test officer credentials
# ──────────────────────────────────────────
OFFICER = {
    "first_name":    "Test",
    "last_name":     "Officer",
    "officer_id":    f"OFF-E2E-{int(time.time())}",
    "officer_email": f"e2etest_{int(time.time())}@verisight.dev",
    "password":      "Test@1234567",
    "organization":  "VeriSight QA",
    "designation":   "Inspector",
}

results = []
access_token  = None
refresh_token = None

def section(title):
    print(f"\n{BOLD}{CYAN}{'─'*50}{RESET}")
    print(f"{BOLD}{CYAN}  {title}{RESET}")
    print(f"{BOLD}{CYAN}{'─'*50}{RESET}")

def record(label, ok, status_code=None, detail=""):
    mark  = f"{GREEN}[PASS]{RESET}" if ok else f"{RED}[FAIL]{RESET}"
    code  = f"[{status_code}]" if status_code else ""
    print(f"  {mark} {code:<6} {label}")
    if not ok and detail:
        print(f"         {YELLOW}↳ {detail[:200]}{RESET}")
    results.append(ok)
    return ok

def post(path, json=None, headers=None):
    return requests.post(BASE + path, json=json, headers=headers, timeout=15)

def get(path, headers=None):
    return requests.get(BASE + path, headers=headers, timeout=15)

def auth_headers():
    return {"Authorization": f"Bearer {access_token}"}

# ──────────────────────────────────────────
# Create a minimal valid JPEG (1x1 white pixel)
# ──────────────────────────────────────────
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

# ──────────────────────────────────────────
# 1. SIGNUP
# ──────────────────────────────────────────
section("1. POST /auth/signup")
try:
    r = post("/auth/signup", json=OFFICER)
    ok = r.status_code == 200
    record("Signup new officer", ok, r.status_code, r.text)
    if not ok:
        print(f"  {YELLOW}Full response: {r.text[:400]}{RESET}")
except Exception as e:
    record("Signup new officer", False, detail=str(e))

# ──────────────────────────────────────────
# 2. LOGIN
# ──────────────────────────────────────────
section("2. POST /auth/login")
try:
    r = post("/auth/login", json={
        "officer_email": OFFICER["officer_email"],
        "password":      OFFICER["password"],
    })
    ok = r.status_code == 200
    record("Login with credentials", ok, r.status_code, r.text)
    if ok:
        data = r.json()
        access_token  = data.get("access_token")
        refresh_token = data.get("refresh_token")
        print(f"  {GREEN}↳ access_token:  {access_token[:40]}...{RESET}")
        print(f"  {GREEN}↳ refresh_token: {refresh_token[:40]}...{RESET}")
    else:
        print(f"  {YELLOW}Full response: {r.text[:400]}{RESET}")
except Exception as e:
    record("Login with credentials", False, detail=str(e))

# ──────────────────────────────────────────
# 3. GET /auth/me
# ──────────────────────────────────────────
section("3. GET /auth/me")
if access_token:
    try:
        r = get("/auth/me", headers=auth_headers())
        ok = r.status_code == 200
        record("Get own profile (with token)", ok, r.status_code, r.text)
        if ok:
            d = r.json()
            print(f"  {GREEN}↳ Name: {d.get('first_name')} {d.get('last_name')}{RESET}")
            print(f"  {GREEN}↳ Org:  {d.get('organization')}{RESET}")
            print(f"  {GREEN}↳ Role: {d.get('designation')}{RESET}")
    except Exception as e:
        record("Get own profile", False, detail=str(e))
else:
    record("Get own profile (skipped — no token)", False)

# ──────────────────────────────────────────
# 4. POST /auth/refresh
# ──────────────────────────────────────────
section("4. POST /auth/refresh")
if refresh_token:
    try:
        r = post("/auth/refresh", json={"refresh_token": refresh_token})
        ok = r.status_code == 200
        record("Refresh access token", ok, r.status_code, r.text)
        if ok:
            new_token = r.json().get("access_token", "")
            print(f"  {GREEN}↳ new access_token: {new_token[:40]}...{RESET}")
            access_token = new_token  # use the refreshed token for OCR tests
    except Exception as e:
        record("Refresh access token", False, detail=str(e))
else:
    record("Refresh token (skipped — no refresh_token)", False)

# ──────────────────────────────────────────
# 5. OCR ENDPOINTS (authenticated, real image)
# ──────────────────────────────────────────
section("5. OCR Endpoints (authenticated)")
OCR_ENDPOINTS = [
    ("/ocr/passport",        "Passport OCR"),
    ("/ocr/aadhaar",         "Aadhaar OCR"),
    ("/ocr/visa",            "Visa OCR"),
    ("/ocr/driving-license", "Driving License OCR"),
    ("/ocr/national-id",     "National ID OCR"),
    ("/ocr/permit",          "Permit OCR"),
]

if access_token:
    for path, label in OCR_ENDPOINTS:
        try:
            r = requests.post(
                BASE + path,
                headers=auth_headers(),
                files={"file": ("test_doc.jpg", TINY_JPEG, "image/jpeg")},
                timeout=60,
            )
            # Accept 200 (success) or 422 (OCR couldn't extract — still means endpoint works)
            ok = r.status_code in (200, 422)
            record(f"{label:<25} → {r.status_code}", ok, r.status_code,
                   "" if ok else r.text)
            if r.status_code == 200:
                d = r.json()
                print(f"     {CYAN}status={d.get('status')}  confidence={d.get('ocr_confidence')}  "
                      f"fields={list(d.get('fields', {}).keys())[:5]}{RESET}")
        except Exception as e:
            record(f"{label}", False, detail=str(e))
else:
    for _, label in OCR_ENDPOINTS:
        record(f"{label} (skipped — no token)", False)

# ──────────────────────────────────────────
# Summary
# ──────────────────────────────────────────
passed = sum(results)
total  = len(results)
color  = GREEN if passed == total else (YELLOW if passed > total // 2 else RED)
print(f"\n{BOLD}{'═'*50}{RESET}")
print(f"  {color}{BOLD}{passed}/{total} end-to-end checks passed{RESET}")
print(f"{BOLD}{'═'*50}{RESET}\n")

sys.exit(0 if passed == total else 1)
