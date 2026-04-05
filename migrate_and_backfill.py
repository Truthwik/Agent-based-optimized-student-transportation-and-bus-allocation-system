"""
migrate_and_backfill.py
-----------------------
Step 1: ALTER TABLE route_stops → add scheduled_departure column if missing
Step 2: Compute backward-ETA departure times for all existing route_stop rows
        that have NULL scheduled_departure and save them to the DB.

Run from the project root:
    python migrate_and_backfill.py
"""

import sys
import os
import math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.database import SessionLocal, engine
from backend.models.models import Route, RouteStop, Stop
from backend.config import (
    CAMPUS_LAT,
    CAMPUS_LNG,
    CAMPUS_ARRIVAL_MIN_MINUTES,
    CAMPUS_ARRIVAL_MAX_MINUTES,
)
from sqlalchemy import text

AVG_SPEED_KMPH = 35.0
DWELL_TIME_MINUTES = 2.0


# ─── Helpers ──────────────────────────────────────────────────────────────────

def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return R * 2.0 * math.asin(math.sqrt(a))


def mins_to_display(total_mins: int) -> str:
    hour = (total_mins // 60) % 24
    minute = total_mins % 60
    period = "AM" if hour < 12 else "PM"
    display_hour = hour if hour <= 12 else hour - 12
    if display_hour == 0:
        display_hour = 12
    return f"{display_hour:02d}:{minute:02d} {period}"


def target_arrival_for_bus(bus_id: int) -> int:
    window_span = max(0, int(CAMPUS_ARRIVAL_MAX_MINUTES) - int(CAMPUS_ARRIVAL_MIN_MINUTES))
    stagger = (bus_id * 7) % (window_span + 1) if window_span > 0 else 0
    target = int(CAMPUS_ARRIVAL_MIN_MINUTES) + stagger
    return max(int(CAMPUS_ARRIVAL_MIN_MINUTES), min(int(CAMPUS_ARRIVAL_MAX_MINUTES), target))


def compute_departure_times(rss, stop_map, bus_id):
    route_sequence = [rs.stop_id for rs in rss]
    n = len(route_sequence)
    departure_minutes = [0.0] * n
    current_time = float(target_arrival_for_bus(bus_id))

    # Last stop → campus
    last = stop_map[route_sequence[-1]]
    seg = haversine_km(float(last.latitude), float(last.longitude), float(CAMPUS_LAT), float(CAMPUS_LNG))
    current_time -= (seg / AVG_SPEED_KMPH) * 60.0 + DWELL_TIME_MINUTES
    departure_minutes[-1] = current_time

    # Walk backwards
    for k in range(n - 2, -1, -1):
        sa = stop_map[route_sequence[k]]
        sb = stop_map[route_sequence[k + 1]]
        seg = haversine_km(float(sa.latitude), float(sa.longitude), float(sb.latitude), float(sb.longitude))
        current_time -= (seg / AVG_SPEED_KMPH) * 60.0 + DWELL_TIME_MINUTES
        departure_minutes[k] = current_time

    return [mins_to_display(int(round(m))) for m in departure_minutes]


# ─── Step 1: ALTER TABLE if column is missing ─────────────────────────────────

def ensure_column_exists():
    with engine.connect() as conn:
        # Check if the column already exists
        result = conn.execute(text(
            "SELECT COUNT(*) FROM information_schema.columns "
            "WHERE table_schema = DATABASE() "
            "AND table_name = 'route_stops' "
            "AND column_name = 'scheduled_departure'"
        ))
        count = result.scalar()
        if count == 0:
            print("[migrate] Column 'scheduled_departure' not found; adding...")
            conn.execute(text(
                "ALTER TABLE route_stops ADD COLUMN scheduled_departure VARCHAR(20) NULL"
            ))
            conn.commit()
            print("[migrate] Column added successfully.")
        else:
            print("[migrate] Column 'scheduled_departure' already exists.")


# ─── Step 2: Backfill NULL rows ───────────────────────────────────────────────

def backfill():
    db = SessionLocal()
    try:
        routes = db.query(Route).all()
        total_updated = 0
        total_skipped = 0

        for route in routes:
            rss = (
                db.query(RouteStop)
                .filter(RouteStop.route_id == route.route_id)
                .order_by(RouteStop.stop_order)
                .all()
            )
            if not rss:
                continue

            null_rows = [rs for rs in rss if not rs.scheduled_departure]
            if not null_rows:
                total_skipped += len(rss)
                continue

            stop_ids = [rs.stop_id for rs in rss]
            stops = db.query(Stop).filter(Stop.stop_id.in_(stop_ids)).all()
            stop_map = {s.stop_id: s for s in stops}

            missing = [sid for sid in stop_ids if sid not in stop_map]
            if missing:
                print(f"  [WARN] Route {route.route_id}: missing stop coords for IDs {missing}, skipping.")
                continue

            dep_times = compute_departure_times(rss, stop_map, route.bus_id)

            for rs, dep in zip(rss, dep_times):
                if not rs.scheduled_departure:
                    rs.scheduled_departure = dep
                    total_updated += 1

            print(
                f"  Route {route.route_id} (Bus {route.bus_id}): "
                f"filled {len(null_rows)} stops → {dep_times}"
            )

        db.commit()
        print(f"\n[OK] Backfill complete: {total_updated} rows updated, {total_skipped} already had times.")

    except Exception as e:
        db.rollback()
        print(f"\n[ERROR] Backfill error: {e}")
        raise
    finally:
        db.close()


# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n=== BVRIT Bus — route_stops Migration & Backfill ===\n")
    ensure_column_exists()
    print("\nBackfilling departure times...\n")
    backfill()
    print("\nDone. Restart your FastAPI server and check the bus pass page.")
