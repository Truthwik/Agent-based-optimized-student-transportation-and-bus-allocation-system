import sys
import os
import csv
import random
from pathlib import Path

# Add root to python path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from backend.database import SessionLocal  # type: ignore
from backend.models.models import Stop, Student  # type: ignore

def update_data():
    db = SessionLocal()
    try:
        data_dir = Path(__file__).resolve().parent / "data"
        stops_file = data_dir / "stopsupdated.csv"
        students_file = data_dir / "generated_students.csv"

        valid_stop_ids = []
        
        # 1. Update Stops in DB
        with open(stops_file, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                s_id = int(row['stop_id'])
                s_name = row['Stop Name']
                lat = float(row['Latitude'])
                lon = float(row['Longitude'])
                
                stop = db.query(Stop).filter(Stop.stop_id == s_id).first()
                if stop:
                    stop.stop_name = s_name
                    stop.latitude = lat
                    stop.longitude = lon
                else:
                    new_stop = Stop(
                        stop_id=s_id,
                        stop_name=s_name,
                        latitude=lat,
                        longitude=lon
                    )
                    db.add(new_stop)
                valid_stop_ids.append(s_id)
        
        # Flush to make sure new stops are in DB before updating students
        db.flush()
        print(f"Updated {len(valid_stop_ids)} stops in the database.")
        
        # 2. Update generated_students.csv
        students_data = []
        student_stop_map = {}
        with open(students_file, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            for row in reader:
                # Assign a random valid stop
                new_stop_id = random.choice(valid_stop_ids)
                row['stop_id'] = new_stop_id
                students_data.append(row)
                student_stop_map[row['student_id']] = new_stop_id
                
        with open(students_file, mode='w', newline='', encoding='utf-8') as f:
            if fieldnames is None:
                fieldnames = ["student_id", "name", "branch", "year_of_study", "joining_year", "phone", "password", "stop_id"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(students_data)
            
        print("Updated generated_students.csv with valid stop_ids.")

        # 3. Update students in database
        db_students = db.query(Student).all()
        updated_students_count = 0
        for st in db_students:
            if st.student_id in student_stop_map:
                st.stop_id = student_stop_map[st.student_id]
                updated_students_count = updated_students_count + 1  # type: ignore
                
        print(f"Updated {updated_students_count} students in the db with valid stop_ids.")
        
        # Commit changes
        db.commit()
        
        # 4. Clean up old stops
        old_stops = db.query(Stop).filter(~Stop.stop_id.in_(valid_stop_ids)).all()
        if old_stops:
            from backend.models.models import RouteStop, Route, Allocation  # type: ignore
            db.query(RouteStop).delete()
            db.query(Route).delete()
            db.query(Allocation).delete()
            for st in db_students:
                st.allocated_bus_id = None
            
            old_stops_count = len(old_stops)
            for os_st in old_stops:
                db.delete(os_st)
            db.commit()
            print(f"Cleaned up {old_stops_count} old stops no longer in use.")

        print("Data update script finished successfully!")
        
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    update_data()
