
import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add the project root to sys.path to import backend modules
sys.path.append(r'c:\Users\lenovo\Desktop\Bvrit_bus_Optimizer')

from backend.config import DATABASE_URL
from backend.models.models import Student, Admin, Stop

def check_stops():
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    print("\n--- Stops with 'College' or 'Campus' in Name ---")
    stops = session.query(Stop).filter(Stop.stop_name.like('%college%') | Stop.stop_name.like('%campus%') | Stop.stop_name.like('%bvrit%')).all()
    for s in stops:
        print(f"ID: {s.stop_id} | Name: {s.stop_name}")

    session.close()

if __name__ == "__main__":
    check_stops()
