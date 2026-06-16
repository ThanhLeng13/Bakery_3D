"""
Apply loyalty RPC functions using Supabase service_role JWT as a raw HTTP POST
to the PostgREST /rpc/exec endpoint, then fall back to using pg_query via REST.

This uses the Supabase service key which has PostgreSQL superuser equivalent access.
"""
import json, urllib.request, urllib.error

import os
from dotenv import load_dotenv

load_dotenv()

SQL_FILE = "migrations/add_loyalty_rpcs.sql"
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
# Service role key (bypasses RLS, has DDL if configured)
SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

sql = open(SQL_FILE, encoding="utf-8").read()
print(f"Applying {len(sql)} chars of SQL...")

# Strategy: call an existing RPC that executes raw SQL.
# The Supabase service_role JWT can call postgres via PostgREST extensions.
# We'll try the "sql" function if available, else pg_query.

from supabase import create_client
db = create_client(SUPABASE_URL, SERVICE_KEY)

# Split on statement boundaries and call each via a helper
stmts = [s.strip() for s in sql.split(";") if s.strip() and not s.strip().startswith("--")]

for i, stmt in enumerate(stmts):
    if not stmt:
        continue
    print(f"\n--- Statement {i+1} ---\n{stmt[:80]}...")
    try:
        # Try exec_sql RPC if it exists
        result = db.rpc("exec_sql", {"query": stmt + ";"}).execute()
        print(f"  OK via exec_sql: {result.data}")
    except Exception as e1:
        # Try query RPC
        try:
            result = db.rpc("query", {"sql": stmt + ";"}).execute()
            print(f"  OK via query rpc: {result.data}")
        except Exception as e2:
            print(f"  Both failed:\n    exec_sql: {str(e1)[:100]}\n    query: {str(e2)[:100]}")
