
import sys
import random
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.append(r'c:\Users\lenovo\Desktop\Bvrit_bus_Optimizer')
from backend.config import DATABASE_URL
from backend.models.models import Student, Stop

def reassign_bvrit_students():
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Find the BVRIT stop ID (detected as 28 previously)
    bvrit_stop_id = 28
    
    # Get all other valid stop IDs
    all_stops = session.query(Stop).filter(Stop.stop_id != bvrit_stop_id).all()
    if not all_stops:
        print("No other stops found.")
        return
        
    other_stop_ids = [s.stop_id for s in all_stops]
    
    # Find students with BVRIT stop
    students = session.query(Student).filter(Student.stop_id == bvrit_stop_id).all()
    print(f"Reassigning {len(students)} students who had BVRIT selected...")
    
    for s in students:
        new_stop_id = random.choice(other_stop_ids)
        new_stop = session.query(Stop).filter(Stop.stop_id == new_stop_id).first()
        old_name = "BVRIT"
        s.stop_id = new_stop_id
        # Also clear allocation to trigger re-optimization
        s.allocated_bus_id = None
        print(f"Student: {s.name} | Old: {old_name} -> New: {new_stop.stop_name} (ID: {new_stop_id})")
        
    session.commit()
    print("Reassignment complete and committed.")
    session.close()

if __name__ == "__main__":
    reassign_bvrit_students()
