"""
check_db.py
-----------
Verifies PostgreSQL connectivity and lists all tables + row counts.
Run from the project root:
    python check_db.py
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')   # force UTF-8 output on Windows
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text, inspect
from backend.database import engine
from backend.config import DB_HOST, DB_PORT, DB_USER, DB_NAME, DATABASE_URL

print("\n" + "=" * 60)
print("  BVRIT Bus -- PostgreSQL Connection & Data Check")
print("=" * 60)
print(f"  Host     : {DB_HOST}")
print(f"  Port     : {DB_PORT}")
print(f"  User     : {DB_USER}")
print(f"  Database : {DB_NAME}")
print(f"  URL      : {DATABASE_URL}")
print("=" * 60)

# -- 1. Connection test -------------------------------------------------------
print("\n[1] Testing connection...")
try:
    with engine.connect() as conn:
        pg_version = conn.execute(text("SELECT version()")).scalar()
    print(f"    [OK] Connected! PostgreSQL version:\n       {pg_version}")
except Exception as e:
    print(f"    [FAIL] Connection FAILED: {e}")
    sys.exit(1)

# -- 2. List all tables & row counts -----------------------------------------
print("\n[2] Tables in database:")
try:
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    if not tables:
        print("    [WARN] No tables found -- run migrate_and_backfill.py first.")
    else:
        with engine.connect() as conn:
            print(f"    {'Table':<30} {'Row Count':>10}")
            print(f"    {'-'*30} {'-'*10}")
            for table in sorted(tables):
                count = conn.execute(text(f'SELECT COUNT(*) FROM "{table}"')).scalar()
                print(f"    {table:<30} {count:>10}")
except Exception as e:
    print(f"    [FAIL] Error inspecting tables: {e}")
    sys.exit(1)

# -- 3. Quick data samples ----------------------------------------------------
print("\n[3] Sample data check:")
checks = [
    ("admins",     "SELECT username FROM admins LIMIT 3"),
    ("students",   "SELECT student_id, name FROM students LIMIT 3"),
    ("buses",      "SELECT bus_id, bus_number FROM buses LIMIT 3"),
    ("stops",      "SELECT stop_id, stop_name FROM stops LIMIT 3"),
    ("routes",     "SELECT route_id, bus_id, total_stops FROM routes LIMIT 3"),
]
with engine.connect() as conn:
    for label, query in checks:
        try:
            rows = conn.execute(text(query)).fetchall()
            if rows:
                print(f"    [DATA] {label}: {[dict(r._mapping) for r in rows]}")
            else:
                print(f"    [EMPTY] {label}: (no data yet)")
        except Exception as e:
            print(f"    [WARN]  {label}: {e}")

print("\n" + "=" * 60)
print("  Check complete.")
print("=" * 60 + "\n")
