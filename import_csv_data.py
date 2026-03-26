import sys
import os
import csv
from pathlib import Path

# Add root to python path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from backend.database import SessionLocal  # type: ignore
from backend.models.models import Stop, Bus  # type: ignore

def import_data():
    db = SessionLocal()
    try:
        data_dir = Path(__file__).resolve().parent / "data"
        stops_file = data_dir / "stops.csv"
        buses_file = data_dir / "buses new.csv"

        stops_imported = 0
        buses_imported = 0

        # Import Stops
        if stops_file.exists():
            with open(stops_file, mode='r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    stop = db.query(Stop).filter(Stop.stop_id == int(row['stop_id'])).first()
                    if not stop:
                        new_stop = Stop(
                            stop_id=int(row['stop_id']),
                            stop_name=row['stop_name'],
                            latitude=float(row['latitude']),
                            longitude=float(row['longitude'])
                        )
                        db.add(new_stop)
                        stops_imported = stops_imported + 1  # type: ignore
            print(f"{stops_imported} new stops staged for import.")
        else:
            print(f"File not found: {stops_file}")

        # Import Buses
        if buses_file.exists():
            with open(buses_file, mode='r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    bus = db.query(Bus).filter(Bus.bus_id == int(row['bus_id'])).first()
                    if not bus:
                        new_bus = Bus(
                            bus_id=int(row['bus_id']),
                            bus_number=row['bus_number'],
                            capacity=int(row['capacity']),
                            driver_name=row['driver_name'],
                            driver_phone=row['driver_phone']
                        )
                        db.add(new_bus)
                        buses_imported = buses_imported + 1  # type: ignore
            print(f"{buses_imported} new buses staged for import.")
        else:
             print(f"File not found: {buses_file}")
        
        db.commit()
        print("Database commit successful. Data imported!")
    except Exception as e:
        db.rollback()
        print(f"Error importing data: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    import_data()
