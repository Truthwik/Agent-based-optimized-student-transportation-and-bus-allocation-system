import sys
import os
import random
import csv
from pathlib import Path

# Add root to python path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from backend.database import SessionLocal  # type: ignore
from backend.models.models import Student, Stop  # type: ignore

def generate_students():
    db = SessionLocal()
    try:
        # Get all valid stop IDs
        stops = db.query(Stop).all()
        stop_ids = [int(s.stop_id) for s in stops if s.stop_id is not None]
        if not stop_ids:
            print("No stops found in the database. Please import stops first.")
            return

        # 4 batches: 20, 21, 22, 23
        joining_years = [20, 21, 22, 23] 
        # Map branches to letter codes
        branches = {
            "CSE": "A", "ECE": "B", "EEE": "C", "MECH": "D", 
            "CIVIL": "E", "IT": "F", "AIDS": "G", "AIML": "H"
        }
        
        first_names = ["Rahul", "Priya", "Aryan", "Anjali", "Karthik", "Sneha", "Rohit", "Neha", "Arjun", "Kavya", "Siddharth", "Divya", "Varun", "Riya", "Aditya", "Swati", "Nikhil", "Pooja", "Vikram", "Meghana"]
        last_names = ["Reddy", "Rao", "Sharma", "Yadav", "Patil", "Deshmukh", "Chowdary", "Goud", "Naidu", "Verma", "Agarwal", "Gupta", "Kumar", "Singh"]

        students_created = 0
        students_data_for_csv = []
        
        # Clear existing students if any, to avoid primary key collisions when rerunning
        db.query(Student).delete()
        db.commit()

        # 2000 members / 4 years = 500 per year. 500 / 8 branches = ~62 per branch per year.
        # We will generate 62 students for each branch and each year, resulting in exactly (62 * 8 * 4) = 1984 students (Close to 2000).
        for year in joining_years:
            # Calculate current year of study (Assuming current year is 2024 for academic context)
            # 23 = 1st year, 22 = 2nd year, 21 = 3rd year, 20 = 4th year
            academic_year = 1 if year == 23 else (2 if year == 22 else (3 if year == 21 else 4))
            
            for branch_name, branch_code in branches.items():
                start_roll = 1
                for i in range(start_roll, start_roll + 63):
                    # Format: ##211X####
                    roll_no = f"{year}211{branch_code}{str(i).zfill(4)}"
                    name = f"{random.choice(first_names)} {random.choice(last_names)}"
                    phone = f"9{random.randint(100000000, 999999999)}"
                    assigned_stop = random.choice(stop_ids)
                    
                    student = Student(
                        student_id=roll_no,
                        name=name,
                        branch=branch_name,
                        year=academic_year,
                        phone=phone,
                        password="bvrit123",  # Changed to fixed password for all students
                        bus_required=True,
                        stop_id=assigned_stop,
                        allocated_bus_id=None
                    )
                    db.add(student)
                    
                    students_data_for_csv.append({
                        "student_id": roll_no,
                        "name": name,
                        "branch": branch_name,
                        "year_of_study": academic_year,
                        "joining_year": f"20{year}",
                        "phone": phone,
                        "password": "bvrit123",
                        "stop_id": assigned_stop
                    })
                    students_created = students_created + 1  # type: ignore

        db.commit()
        print(f"Successfully generated and inserted {students_created} students evenly distributed into the database.")
        
        # Output CSV for easy Excel color-coding
        data_dir = Path(__file__).resolve().parent / "data"
        data_dir.mkdir(exist_ok=True)
        csv_path = data_dir / "generated_students.csv"
        
        with open(csv_path, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                "student_id", "name", "branch", "year_of_study", "joining_year", "phone", "password", "stop_id"
            ])
            writer.writeheader()
            writer.writerows(students_data_for_csv)
            
        print(f"A perfect dataset was also saved to {csv_path} so you can easily color-code the rows by 'year_of_study' in Excel!")

    except Exception as e:
        db.rollback()
        print(f"Error generating students: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    generate_students()
