import sys
import os
from sqlalchemy import text

# Add parent dir to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from backend.database import engine

def migrate():
    with engine.connect() as conn:
        print("Starting manual migration...")
        
        # 1. Add allocation_type to students
        try:
            conn.execute(text("ALTER TABLE students ADD COLUMN allocation_type VARCHAR(20) DEFAULT NULL"))
            conn.commit()
            print("Added allocation_type column to students table.")
        except Exception as e:
            print(f"Skipping students.allocation_type: {e}")

        # 2. Create day_pass_bookings table
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS day_pass_bookings (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    student_id VARCHAR(20) NOT NULL,
                    bus_id INT NOT NULL,
                    stop_id INT NOT NULL,
                    booking_date VARCHAR(10) NOT NULL,
                    razorpay_payment_id VARCHAR(100),
                    razorpay_order_id VARCHAR(100),
                    status VARCHAR(20) DEFAULT 'pending',
                    created_at VARCHAR(30),
                    FOREIGN KEY (student_id) REFERENCES students(student_id),
                    FOREIGN KEY (bus_id) REFERENCES buses(bus_id),
                    FOREIGN KEY (stop_id) REFERENCES stops(stop_id)
                )
            """))
            conn.commit()
            print("Created day_pass_bookings table.")
        except Exception as e:
            print(f"Error creating day_pass_bookings: {e}")

        # 3. Create bus_daily_capacity table
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS bus_daily_capacity (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    bus_id INT NOT NULL,
                    travel_date VARCHAR(10) NOT NULL,
                    booked_seats INT DEFAULT 0,
                    UNIQUE KEY unique_bus_date (bus_id, travel_date),
                    FOREIGN KEY (bus_id) REFERENCES buses(bus_id)
                )
            """))
            conn.commit()
            print("Created bus_daily_capacity table.")
        except Exception as e:
            print(f"Error creating bus_daily_capacity: {e}")
            
        print("Migration complete.")

if __name__ == "__main__":
    migrate()
