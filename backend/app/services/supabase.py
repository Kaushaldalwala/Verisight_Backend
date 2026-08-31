"""
supabase.py

Creates two Supabase clients:
  - supabase       : anon/publishable key  (for auth flows on behalf of the user)
  - supabase_admin : service-role/secret key (for server-side DB operations that
                     bypass RLS, e.g. inserting officer profiles after signup)
"""

import os

from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "") or os.getenv("SUPABASE_PUBLISHABLE_KEY", "")
SUPABASE_SECRET_KEY: str = os.getenv("SUPABASE_SECRET_KEY", "")

if not SUPABASE_URL or not SUPABASE_KEY or not SUPABASE_SECRET_KEY:
    raise RuntimeError(
        "Missing Supabase environment variables. "
        "Check your .env file: SUPABASE_URL, SUPABASE_KEY (or SUPABASE_PUBLISHABLE_KEY), SUPABASE_SECRET_KEY"
    )

# Anon client — used for auth (sign_up / sign_in / get_user)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Admin client — service role, bypasses RLS for server-side DB writes
supabase_admin: Client = create_client(SUPABASE_URL, SUPABASE_SECRET_KEY)
