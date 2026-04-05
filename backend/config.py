import os
from dotenv import load_dotenv
from pathlib import Path

# Load .env from project root
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# Database
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "bvrit_bus_db")

DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# JWT
JWT_SECRET = os.getenv("JWT_SECRET", "default_secret")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

# Campus
CAMPUS_NAME = os.getenv("CAMPUS_NAME", "BVRIT Narsapur")
# Verified via Google Maps: Vishnupur, Narsapur, Tuljaraopet, Telangana 502313
CAMPUS_LAT = float(os.getenv("CAMPUS_LAT", "17.7252584"))
CAMPUS_LNG = float(os.getenv("CAMPUS_LNG", "78.2571511"))

def _parse_hhmm_to_minutes(value: str, *, default_minutes: int) -> int:
    """
    Parse 'HH:MM' (24h) into minutes since midnight.
    Falls back to default_minutes if value is missing/invalid.
    """
    try:
        parts = value.strip().split(":")
        if len(parts) != 2:
            return default_minutes
        hh = int(parts[0])
        mm = int(parts[1])
        if not (0 <= hh <= 23 and 0 <= mm <= 59):
            return default_minutes
        return hh * 60 + mm
    except Exception:
        return default_minutes

# Campus arrival window (minutes since midnight)
# Bus(ses) should arrive within this window.
# Default keeps arrivals in the final 10 minutes before 9:00 AM.
# Override via env (24h format): CAMPUS_ARRIVAL_MIN=08:50, CAMPUS_ARRIVAL_MAX=09:00
CAMPUS_ARRIVAL_MIN_MINUTES = _parse_hhmm_to_minutes(
    os.getenv("CAMPUS_ARRIVAL_MIN", "08:50"),
    default_minutes=8 * 60 + 50,
)
CAMPUS_ARRIVAL_MAX_MINUTES = _parse_hhmm_to_minutes(
    os.getenv("CAMPUS_ARRIVAL_MAX", "09:00"),
    default_minutes=9 * 60,
)

# OSRM — local Docker server (see setup_osrm.sh)
OSRM_BASE_URL = os.getenv("OSRM_BASE_URL", "http://localhost:5000")
OSRM_TIMEOUT = int(os.getenv("OSRM_TIMEOUT", "10"))          # seconds per request
OSRM_MAX_RETRIES = int(os.getenv("OSRM_MAX_RETRIES", "2"))   # retry before Haversine fallback

# Razorpay
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")
DAY_PASS_FARE = int(os.getenv("DAY_PASS_FARE", "50"))

# Tracking Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
GPS_PING_INTERVAL_SECONDS = int(os.getenv("GPS_PING_INTERVAL_SECONDS", "8"))
GEOFENCE_RADIUS_METERS = int(os.getenv("GEOFENCE_RADIUS_METERS", "500"))
