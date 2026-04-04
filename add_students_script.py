import sys
import os

# Add the parent directory to sys.path to allow importing from backend
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.database import SessionLocal
from backend.models.models import Student

def add_students():
    db = SessionLocal()
    try:
        students = [
            Student(
                student_id="21211A0501",
                name="Rahul Sharma",
                branch="CSE",
                year=4,
                phone="9876543201",
                password="21211A0501",
                bus_required=False,
                stop_id=None,
                allocation_type=None
            ),
            Student(
                student_id="21211A0502",
                name="Ananya Rao",
                branch="ECE",
                year=4,
                phone="9876543202",
                password="21211A0502",
                bus_required=False,
                stop_id=None,
                allocation_type=None
            ),
            Student(
                student_id="21211A0503",
                name="Siddharth V",
                branch="IT",
                year=4,
                phone="9876543203",
                password="21211A0503",
                bus_required=False,
                stop_id=None,
                allocation_type=None
            ),
            Student(
                student_id="21211A0504",
                name="Pooja Hegde",
                branch="EEE",
                year=4,
                phone="9876543204",
                password="21211A0504",
                bus_required=False,
                stop_id=None,
                allocation_type=None
            ),
            Student(
                student_id="21211A0505",
                name="Karthik N",
                branch="MECH",
                year=4,
                phone="9876543205",
                password="21211A0505",
                bus_required=False,
                stop_id=None,
                allocation_type=None
            )
        ]
        
        for student in students:
            # Check if student already exists
            existing = db.query(Student).filter(Student.student_id == student.student_id).first()
            if not existing:
                db.add(student)
                print(f"Added student: {student.name} ({student.student_id})")
            else:
                print(f"Student {student.student_id} already exists.")
        
        db.commit()
        print("Done.")
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    add_students()
