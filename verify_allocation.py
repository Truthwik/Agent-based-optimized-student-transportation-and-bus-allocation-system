import sys
import os
import random

# Add root to python path
sys.path.insert(0, os.path.dirname(__file__))

from backend.database import SessionLocal  # type: ignore
from backend.models.models import Student, Stop  # type: ignore
from backend.services.optimizer_engine import run_optimizer  # type: ignore

def main():
    db = SessionLocal()
    
    # Randomly assign students to require a bus
    students = db.query(Student).all()
    stops = db.query(Stop).all()
    
    if not students or not stops:
        print("No students or stops found in the database. Please add data first.")
        db.close()
        return

    # Verify using strictly existing database records
    requiring_bus = [s for s in students if s.bus_required]
    print(f"Found {len(requiring_bus)} students requiring a bus allocation.")
    
    print("\nRunning Optimizer Engine (Sweep Algorithm + Greedy routing)...\n")
    result = run_optimizer(db)
    
    print(f"Message: {result.get('message', '')}")
    print(f"Total Routes Generated: {len(result.get('routes', []))}")
    print(f"Allocated Students: {result.get('total_students_allocated', 0)}")
    print(f"Unassigned Students: {result.get('total_students_unassigned', 0)}")
    
    print("\n--- Routes ---")
    for idx, r in enumerate(result.get('routes', []), 1):
        print(f"Route {idx} (Bus {r['bus_number']}):")
        print(f"  Capacity: {r['capacity']}, Assigned: {r['students']} ({r['utilization']}%)")
        print(f"  Stops Order ({len(r['stops'])}): " + " -> ".join(r['stops']))

    db.close()

if __name__ == "__main__":
    main()
