
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
sys.path.append(r'c:\Users\lenovo\Desktop\Bvrit_bus_Optimizer')
from backend.config import DATABASE_URL
from backend.models.models import Stop

def list_all_stops():
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    stops = session.query(Stop).all()
    print("--- All Stops ---")
    for s in stops[:10]:
        print(f"ID: {s.stop_id} | Name: {s.stop_name}")
    print(f"({len(stops)} stops total)")
    session.close()

if __name__ == "__main__":
    list_all_stops()
