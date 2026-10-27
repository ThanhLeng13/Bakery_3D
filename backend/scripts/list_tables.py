"""Liệt kê toàn bộ bảng trong CSDL thật, tìm bảng nào liên quan 3D/mẫu."""
import json, os, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")
import supabase

c = supabase.create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])
rows = c.rpc("exec_sql", {"q": "select 1"}).execute() if False else None

# PostgREST khong doi ke bang; dung REST root de xem OpenAPI.
import urllib.request
H = {"apikey": os.environ["SUPABASE_SERVICE_ROLE_KEY"],
     "Authorization": "Bearer " + os.environ["SUPABASE_SERVICE_ROLE_KEY"]}
req = urllib.request.Request(
    os.environ["SUPABASE_URL"].rstrip("/") + "/rest/v1/",
    headers={**H, "Accept": "application/openapi+json"})
try:
    spec = json.load(urllib.request.urlopen(req, timeout=30))
    paths = [p for p in spec.get("paths", {}) if p.startswith("/")]
    print("  bang doc duoc qua REST:")
    for p in sorted(paths):
        print("   ", p)
except Exception as e:
    print("  LOI:", type(e).__name__, str(e)[:150])
