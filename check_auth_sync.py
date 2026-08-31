"""Diagnose officer_profiles vs Supabase auth.users sync."""
import os
import requests
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
admin = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SECRET_KEY"))
BASE = "http://127.0.0.1:8000"

profiles = admin.table("officer_profiles").select("id,officer_id,officer_email").execute().data
users = admin.auth.admin.list_users()
auth_by_id = {u.id: u.email for u in users}

print("=== officer_profiles vs auth.users ===")
for p in profiles:
    uid = p["id"]
    auth_email = auth_by_id.get(uid)
    status = f"OK (auth: {auth_email})" if auth_email else "MISSING auth.users row"
    print(f"  {p['officer_id']:15} {p['officer_email']:35} -> {status}")

print("\n=== login test (Test@1234567) ===")
for p in profiles:
    r = requests.post(
        BASE + "/auth/login",
        json={"officer_email": p["officer_email"], "password": "Test@1234567"},
        timeout=10,
    )
    print(f"  {p['officer_email']}: {r.status_code} {r.text[:100]}")
