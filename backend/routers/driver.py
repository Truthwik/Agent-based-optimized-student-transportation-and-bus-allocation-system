from fastapi import APIRouter, Depends, HTTPException, Header
from datetime import datetime
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.models import Bus, BusLocationHistory
from .auth import decode_token
from ..services.redis_client import set_bus_state, update_bus_location, get_bus_location
from pydantic import BaseModel

router = APIRouter(prefix="/driver", tags=["Driver"])

# In-memory ping counter (works without Redis)
_ping_counts: dict = {}

class LocationUpdate(BaseModel):
    bus_id: int
    latitude: float
    longitude: float
    speed_kmh: float = 0
    accuracy_meters: float = 0


def get_current_driver(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid token")
    token = authorization.split(" ")[1]
    payload = decode_token(token)
    if payload.get("role") != "driver":
        raise HTTPException(status_code=403, detail="Not a driver")
    return payload


@router.post("/trip/start")
def start_trip(driver=Depends(get_current_driver)):
    bus_id = driver.get("bus_id")
    set_bus_state(bus_id, True)
    _ping_counts[bus_id] = 0
    return {"message": "Trip started", "bus_id": bus_id}


@router.post("/trip/end")
def end_trip(driver=Depends(get_current_driver)):
    bus_id = driver.get("bus_id")
    set_bus_state(bus_id, False)
    _ping_counts.pop(bus_id, None)
    return {"message": "Trip ended"}


@router.post("/location")
def update_location(data: LocationUpdate, driver=Depends(get_current_driver), db: Session = Depends(get_db)):
    bus_id = driver.get("bus_id")
    if data.bus_id != bus_id:
        raise HTTPException(status_code=403, detail="Bus ID mismatch")

    location_data = {
        "bus_id": bus_id,
        "latitude": data.latitude,
        "longitude": data.longitude,
        "speed_kmh": data.speed_kmh,
        "accuracy_meters": data.accuracy_meters,
        "updated_at": datetime.now().strftime("%H:%M:%S")
    }

    # Update store (Redis if available, else in-memory)
    update_bus_location(bus_id, location_data)

    # Increment ping count, persist to MySQL every 4th ping (~32s)
    count = _ping_counts.get(bus_id, 0) + 1
    _ping_counts[bus_id] = count

    if count % 4 == 0:
        try:
            db.add(BusLocationHistory(
                bus_id=bus_id,
                latitude=data.latitude,
                longitude=data.longitude,
                speed_kmh=data.speed_kmh,
                accuracy_meters=data.accuracy_meters
            ))
            db.commit()
        except Exception:
            db.rollback()

    return {"status": "ok", "ping": count}


@router.get("/route")
def get_driver_route(driver=Depends(get_current_driver), db: Session = Depends(get_db)):
    bus_id = driver.get("bus_id")
    from ..models.models import Route
    route = db.query(Route).filter(Route.bus_id == bus_id).first()
    if not route:
        return {"message": "No route assigned yet", "stops": []}
    stops = []
    for rs in sorted(route.route_stops, key=lambda x: x.stop_order):
        stops.append({
            "stop_order": rs.stop_order,
            "stop_name": rs.stop.stop_name,
            "latitude": rs.stop.latitude,
            "longitude": rs.stop.longitude,
            "scheduled_departure": rs.scheduled_departure,
        })
    return {
        "route_id": route.route_id,
        "total_stops": route.total_stops,
        "total_students": route.total_students,
        "total_distance": round(route.total_distance, 2),
        "stops": stops
    }
