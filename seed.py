"""
Seed script - populates the database with initial data.
Run: python seed.py
"""
import sys
import os
from pathlib import Path

# Add project root to python path reliably
sys.path.insert(0, str(Path(__file__).resolve().parent))

from backend.database import SessionLocal, engine, Base  # type: ignore
from backend.models.models import Admin, Student, Stop, Bus  # type: ignore

# Create tables
Base.metadata.create_all(bind=engine)
db = SessionLocal()

try:
    # ─── Admin ────────────────────────────────────
    if not db.query(Admin).first():
        admin = Admin(username="admin", password="admin123")
        db.add(admin)
        print("Admin user created (admin/admin123)")



    db.commit()
    print("\nDatabase seeded successfully!")

except Exception as err:  # type: ignore
    db.rollback()
    print(f"Error seeding database: {err}")
    raise
finally:
    db.close()
