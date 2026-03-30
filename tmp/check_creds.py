
import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add the project root to sys.path to import backend modules
sys.path.append(r'c:\Users\lenovo\Desktop\Bvrit_bus_Optimizer')

from backend.config import DATABASE_URL
from backend.models.models import Student, Admin

def get_test_credentials():
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    print("\n--- Student Accounts ---")
    students = session.query(Student).limit(5).all()
    if not students:
        print("No student accounts found in database.")
    for s in students:
        # We don't know the plain password because it's hashed, 
        # but let's see if we have some default ones or if we can see the hashed one
        print(f"ID: {s.student_id} | Name: {s.name}")

    print("\n--- Admin Accounts ---")
    admins = session.query(Admin).limit(5).all()
    if not admins:
        print("No admin accounts found in database.")
    for a in admins:
        print(f"Username: {a.username}")

    session.close()

if __name__ == "__main__":
    get_test_credentials()
