"""
create_officer.py — Create a new officer (bypasses Supabase email rate limit).

Usage:
    python create_officer.py

Edit the OFFICER dict below before running.
"""

import os
import sys
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

# ── Edit these values for each new officer ──
OFFICER = {
    "first_name":    "Rahul",
    "last_name":     "Sharma",
    "officer_id":    "OFF-102",          # must be unique
    "officer_email": "rahul.sharma@verisight.dev",  # must be unique
    "password":      "SecurePass@123",   # min 8 chars
    "organization":  "Border Security",
    "designation":   "Inspector",
}


def main() -> int:
    url = os.getenv("SUPABASE_URL")
    secret = os.getenv("SUPABASE_SECRET_KEY")
    if not url or not secret:
        print("ERROR: Missing SUPABASE_URL or SUPABASE_SECRET_KEY in .env")
        return 1

    admin = create_client(url, secret)

    # Check if officer_id or email already exists
    existing = (
        admin.table("officer_profiles")
        .select("officer_id, officer_email")
        .or_(f"officer_id.eq.{OFFICER['officer_id']},officer_email.eq.{OFFICER['officer_email']}")
        .execute()
    )
    if existing.data:
        print(f"ERROR: Officer already exists: {existing.data}")
        return 1

    print(f"Creating auth user: {OFFICER['officer_email']} ...")
    try:
        created = admin.auth.admin.create_user({
            "email":         OFFICER["officer_email"],
            "password":      OFFICER["password"],
            "email_confirm": True,
        })
    except Exception as exc:
        print(f"ERROR creating auth user: {exc}")
        return 1

    user_id = created.user.id
    print(f"Auth user created: {user_id}")

    profile = {
        "id":            user_id,
        "first_name":    OFFICER["first_name"],
        "last_name":     OFFICER["last_name"],
        "officer_id":    OFFICER["officer_id"],
        "officer_email": OFFICER["officer_email"],
        "organization":  OFFICER["organization"],
        "designation":   OFFICER["designation"],
    }

    print("Inserting officer profile ...")
    try:
        resp = admin.table("officer_profiles").insert(profile).execute()
    except Exception as exc:
        print(f"ERROR inserting profile: {exc}")
        print("Rolling back auth user ...")
        try:
            admin.auth.admin.delete_user(user_id)
        except Exception:
            pass
        return 1

    print("\n✅ Officer created successfully!")
    print(f"   Officer ID : {OFFICER['officer_id']}")
    print(f"   Email      : {OFFICER['officer_email']}")
    print(f"   Password   : {OFFICER['password']}")
    print("\nNow login in Swagger with POST /auth/login:")
    print(f'   {{"officer_email": "{OFFICER["officer_email"]}", "password": "{OFFICER["password"]}"}}')
    return 0


if __name__ == "__main__":
    sys.exit(main())
