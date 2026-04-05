from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.orm import Session
import json, asyncio
from ..database import get_db
from ..models.models import Bus, Student
from .auth import decode_token
from ..services.redis_client import get_bus_location, is_bus_active, get_active_buses

router = APIRouter(prefix="/tracking", tags=["Tracking"])


def get_current_user(token: str):
    try:
        return decode_token(token)
    except:
        raise HTTPException(status_code=401, detail="Invalid token")


@router.get("/bus/{bus_id}")
def get_bus_tracking(bus_id: int, token: str = Query(...), db: Session = Depends(get_db)):
    payload = get_current_user(token)
    role = payload.get("role")

    # Students can only track their own allocated bus
    if role == "student":
        student_id = payload.get("sub")
        student = db.query(Student).filter(Student.student_id == student_id).first()
        if not student or student.allocated_bus_id != bus_id:
            raise HTTPException(status_code=403, detail="You can only track your allocated bus")

    is_active = is_bus_active(bus_id)
    location  = get_bus_location(bus_id)

    if not is_active or not location:
        # Bus parked / trip not started
        bus = db.query(Bus).filter(Bus.bus_id == bus_id).first()
        return {
            "bus_id": bus_id,
            "bus_number": bus.bus_number if bus else str(bus_id),
            "is_active": False,
            "status": "parked",
            "message": "Bus is currently in parking"
        }

    location["is_active"] = True
    location["status"] = "active"
    bus = db.query(Bus).filter(Bus.bus_id == bus_id).first()
    if bus:
        location["bus_number"] = bus.bus_number
    return location


@router.get("/fleet")
def get_fleet_tracking(token: str = Query(...), db: Session = Depends(get_db)):
    payload = get_current_user(token)
    if payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Only admins can view the fleet")

    active_buses = get_active_buses()
    results = []
    for loc in active_buses:
        bus_id = loc.get("bus_id")
        bus = db.query(Bus).filter(Bus.bus_id == bus_id).first()
        if bus:
            loc["bus_number"] = bus.bus_number
            results.append(loc)
    return results


@router.websocket("/ws/tracking/{bus_id}")
async def websocket_tracking(websocket: WebSocket, bus_id: int, token: str = Query(...)):
    await websocket.accept()
    try:
        decode_token(token)
    except:
        await websocket.send_text(json.dumps({"error": "Invalid token"}))
        await websocket.close()
        return

    # Send initial location immediately
    loc = get_bus_location(bus_id)
    if loc:
        loc["is_active"] = True
        await websocket.send_text(json.dumps(loc))
    else:
        await websocket.send_text(json.dumps({"bus_id": bus_id, "is_active": False, "status": "parked"}))

    # Poll loop (works without Redis pub/sub)
    try:
        while True:
            await asyncio.sleep(5)
            loc = get_bus_location(bus_id)
            is_active = is_bus_active(bus_id)
            if loc and is_active:
                loc["is_active"] = True
                await websocket.send_text(json.dumps(loc))
            else:
                await websocket.send_text(json.dumps({"bus_id": bus_id, "is_active": False, "status": "parked"}))
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WS error: {e}")
