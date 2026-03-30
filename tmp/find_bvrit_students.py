
import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add the project root to sys.path to import backend modules
sys.path.append(r'c:\Users\lenovo\Desktop\Bvrit_bus_Optimizer')

from backend.config import DATABASE_URL
from backend.models.models import Student, Stop

def check_bvrit_students():
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Find the BVRIT stop
    bvrit_stop = session.query(Stop).filter(Stop.stop_name.ilike('%bvrit%')).filter(Stop.stop_name.not_ilike('%college%')).first()
    if not bvrit_stop:
        print("BVRIT stop not found.")
        return

    print(f"BVRIT Stop ID: {bvrit_stop.stop_id}")
    
    students = session.query(Student).filter(Student.stop_id == bvrit_stop.stop_id).all()
    print(f"Found {len(students)} students with BVRIT stop.")
    for s in students:
        print(f"ID: {s.student_id} | Name: {s.name}")

    session.close()

if __name__ == "__main__":
    check_bvrit_students()
