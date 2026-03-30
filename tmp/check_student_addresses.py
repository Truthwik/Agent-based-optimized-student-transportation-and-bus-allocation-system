
import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.append(r'c:\Users\lenovo\Desktop\Bvrit_bus_Optimizer')
from backend.config import DATABASE_URL
from backend.models.models import Student

def show_addresses():
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    students = session.query(Student).filter(Student.stop_id == 28).all()
    print("--- Students with BVRIT stop ---")
    for s in students:
        print(f"Name: {s.name} | Address: {s.address}")
    session.close()

if __name__ == "__main__":
    show_addresses()
