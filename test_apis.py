"""
test_apis.py — Quick API health check for all VeriSight endpoints.
Run from VeriSight/ directory:
    python test_apis.py
"""

import requests

BASE = "http://localhost:8000"

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

def check(label, method, path, expected_status, **kwargs):
    url = BASE + path
    try:
        resp = requests.request(method, url, timeout=8, **kwargs)
        ok = resp.status_code == expected_status
        color = GREEN if ok else RED
        mark  = "PASS" if ok else "FAIL"
        print(f"  [{mark}] [{resp.status_code}]  {label}")
        if not ok:
            body = resp.text[:200].replace("\n", " ")
            print(f"       -> {body}")
        return ok
    except requests.exceptions.ConnectionError:
        print(f"  [ERR]  {label}  (connection refused)")
        return False
    except Exception as e:
        print(f"  [ERR]  {label}  ({e})")
        return False


print("\n=== VeriSight API Health Check ===")
print(f"Base URL: {BASE}\n")

results = []

print("[ Health ]")
results.append(check("GET  /                ", "GET", "/",              200))
results.append(check("GET  /test-supabase   ", "GET", "/test-supabase", 200))

print("\n[ Auth — invalid/missing body → 422 or 401 ]")
results.append(check("POST /auth/signup  (no body) → 422", "POST", "/auth/signup",  422))
results.append(check("POST /auth/login   (no body) → 422", "POST", "/auth/login",   422))
results.append(check("GET  /auth/me   (no token)   → 401", "GET",  "/auth/me",      401))
results.append(check("POST /auth/refresh (no body) → 422", "POST", "/auth/refresh", 422))

print("\n[ OCR — no token → 401 ]")
for path in ["/ocr/passport", "/ocr/aadhaar", "/ocr/visa",
             "/ocr/driving-license", "/ocr/national-id", "/ocr/permit"]:
    results.append(check(
        f"POST {path:<22} (no token) -> 401",
        "POST", path, 401,
        files={"file": ("test.jpg", b"\xff\xd8\xff", "image/jpeg")}
    ))

print("\n[ Docs ]")
results.append(check("GET  /docs         → 200", "GET", "/docs",         200))
results.append(check("GET  /openapi.json → 200", "GET", "/openapi.json", 200))

passed = sum(1 for r in results if r)
total  = len(results)
print(f"\n{'='*40}")
print(f"  {passed}/{total} checks passed")
print(f"{'='*40}\n")
