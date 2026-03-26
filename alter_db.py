import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from sqlalchemy import text
from backend.database import engine

def alter_db():
    try:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE routes ADD COLUMN total_distance FLOAT DEFAULT 0.0;"))
            print("Successfully added total_distance to routes table.")
    except Exception as e:
        print(f"Error altering table (might already exist): {e}")

if __name__ == "__main__":
    alter_db()
