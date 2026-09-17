"""Apply a SQL migration file to Supabase via the Management API.

The service-role key cannot run DDL (PostgREST rejects it), but a Supabase
Personal Access Token can. This script reads a .sql file and executes it,
printing any database error verbatim so a failure is diagnosable.
"""
import io
import json
import sys
import urllib.error
import urllib.request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

PROJECT_REF = "azdfyzfpwsdgzpfjivtb"


def run_sql(token: str, sql: str):
    req = urllib.request.Request(
        f"https://api.supabase.com/v1/projects/{PROJECT_REF}/database/query",
        data=json.dumps({"query": sql}).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return resp.status, json.loads(resp.read() or b"null")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:1500]


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: apply_migration.py <token> <path.sql>")
        return 2

    token, path = sys.argv[1], sys.argv[2]
    with open(path, encoding="utf-8") as fh:
        sql = fh.read()

    print(f"Applying {path} ({len(sql)} bytes) ...")
    status, body = run_sql(token, sql)
    print(f"HTTP {status}")
    if status >= 400:
        print("FAILED:")
        print(body)
        return 1
    print("OK:", body)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
