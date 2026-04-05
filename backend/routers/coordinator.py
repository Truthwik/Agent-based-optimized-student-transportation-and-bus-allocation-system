from fastapi import APIRouter, Depends, HTTPException, Header, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List
import json
import asyncio

from backend.database import get_db
from backend.models.models import Coordinator, Bus, Student, Allocation, DayPassBooking, Route, RouteStop, Announcement, Complaint
from backend.models.schemas import (
    CoordinatorDashboardResponse, CoordinatorDashboardBus, CoordinatorDashboardSummary,
    CoordinatorResponse, StudentResponse, RouteResponse, RouteStopResponse,
    AnnouncementCreate, AnnouncementResponse, ComplaintResponse, ComplaintResolve
)
from backend.routers.auth import decode_token
from backend.services.redis_client import get_bus_location, is_bus_active

router = APIRouter(prefix="/coordinator", tags=["Coordinator"])

def verify_coordinator(authorization: str = Header(None), token: str = Query(None), db: Session = Depends(get_db)):
    """Verify coordinator from Authorization header or query param."""
    if authorization and authorization.startswith("Bearer "):
        jwt_token = authorization.split(" ")[1]
    elif token:
        jwt_token = token
    else:
        raise HTTPException(status_code=401, detail="Invalid or missing authorization")

    payload = decode_token(jwt_token)
    if payload.get("role") != "coordinator":
        raise HTTPException(status_code=403, detail="Coordinator access required")
    
    coordinator = db.query(Coordinator).filter(Coordinator.employee_id == payload.get("sub")).first()
    if not coordinator or not coordinator.is_active:
        raise HTTPException(status_code=401, detail="Coordinator not found or deactivated")
    
    return coordinator

# ─── 4.1 Dashboard Overview ──────────────────────────
@router.get("/me", response_model=CoordinatorDashboardResponse)
def get_dashboard_summary(db: Session = Depends(get_db), coordinator: Coordinator = Depends(verify_coordinator)):
    bus = coordinator.bus
    if not bus:
        raise HTTPException(status_code=404, detail="No bus assigned to this coordinator")

    # Stats
    yearwise_count = db.query(Allocation).filter(Allocation.bus_id == bus.bus_id).count()
    today = datetime.now().strftime("%Y-%m-%d")
    daypass_count = db.query(DayPassBooking).filter(
        DayPassBooking.bus_id == bus.bus_id,
        DayPassBooking.booking_date == today,
        DayPassBooking.status == 'confirmed'
    ).count()

    total_allocated = yearwise_count + daypass_count
    available_seats = max(0, bus.capacity - total_allocated)
    occupancy = int((total_allocated / bus.capacity) * 100) if bus.capacity > 0 else 0

    open_complaints = db.query(Complaint).filter(
        Complaint.bus_id == bus.bus_id, Complaint.status == 'open'
    ).count()

    now = datetime.now()
    active_announcements = db.query(Announcement).filter(
        Announcement.bus_id == bus.bus_id,
        Announcement.is_active == True,
        Announcement.expires_at > now
    ).count()

    is_live = is_bus_active(bus.bus_id)

    return CoordinatorDashboardResponse(
        coordinator=CoordinatorResponse.model_validate(coordinator),
        bus=CoordinatorDashboardBus(
            bus_number=bus.bus_number,
            max_capacity=bus.capacity,
            driver_name=bus.driver_name,
            driver_phone=bus.driver_phone
        ),
        summary=CoordinatorDashboardSummary(
            total_students_allocated=total_allocated,
            yearwise_students=yearwise_count,
            daypass_students_today=daypass_count,
            available_seats=available_seats,
            occupancy_percent=occupancy,
            bus_is_live=is_live,
            open_complaints=open_complaints,
            active_announcements=active_announcements
        )
    )

# ─── 4.2 Student Details ─────────────────────────────
@router.get("/students")
def get_students(search: str = None, year: int = None, stop_id: int = None, sort: str = None, db: Session = Depends(get_db), coordinator: Coordinator = Depends(verify_coordinator)):
    query = db.query(Student).join(Allocation).filter(Allocation.bus_id == coordinator.bus_id)

    if search:
        query = query.filter((Student.name.ilike(f"%{search}%")) | (Student.student_id.ilike(f"%{search}%")))
    if year:
        query = query.filter(Student.year == year)
    if stop_id:
        query = query.filter(Student.stop_id == stop_id)

    if sort == 'name':
        query = query.order_by(Student.name)

    students = query.all()
    results = []
    for s in students:
        results.append({
            "id": s.student_id,
            "name": s.name,
            "roll_number": s.student_id,
            "year_of_study": s.year,
            "phone": s.phone,
            "stop_name": s.stop.stop_name if s.stop else "Unknown",
            "pickup_time": "08:10:00", # Can be fetched from route mapping
            "allocation_status": "active"
        })
    return results

@router.get("/students/export")
def export_students(db: Session = Depends(get_db), coordinator: Coordinator = Depends(verify_coordinator)):
    from fastapi.responses import PlainTextResponse
    students = db.query(Student).join(Allocation).filter(Allocation.bus_id == coordinator.bus_id).all()
    
    csv_data = "Name,Roll Number,Year,Stop,Phone\n"
    for s in students:
        stop_name = s.stop.stop_name if s.stop else "Unknown"
        csv_data += f"{s.name},{s.student_id},{s.year},{stop_name},{s.phone}\n"

    return PlainTextResponse(content=csv_data, media_type="text/csv", headers={
        "Content-Disposition": f"attachment; filename=bus_{coordinator.bus.bus_number}_students.csv"
    })

# ─── 4.3 Day Pass Details ────────────────────────────
@router.get("/daypass/today")
def get_daypass_today(db: Session = Depends(get_db), coordinator: Coordinator = Depends(verify_coordinator)):
    today = datetime.now().strftime("%Y-%m-%d")
    bookings = db.query(DayPassBooking).filter(
        DayPassBooking.bus_id == coordinator.bus_id,
        DayPassBooking.booking_date == today,
        DayPassBooking.status == 'confirmed'
    ).all()
    
    results = []
    for b in bookings:
        student = b.student
        results.append({
            "booking_id": b.id,
            "student_name": student.name if student else "Unknown",
            "roll_number": student.student_id if student else "Unknown",
            "year_of_study": student.year if student else "-",
            "stop_name": "Mapped Stop", # Needs logic to get stop name
            "payment_id": b.razorpay_payment_id,
            "status": b.status
        })
    return results

# ─── 4.4 Route and Stops ─────────────────────────────
@router.get("/route")
def get_route(db: Session = Depends(get_db), coordinator: Coordinator = Depends(verify_coordinator)):
    route = db.query(Route).filter(Route.bus_id == coordinator.bus_id).first()
    if not route:
        raise HTTPException(status_code=404, detail="No route mapped for this bus")

    stops = []
    for rs in route.route_stops:
        stops.append({
            "sequence": rs.stop_order,
            "stop_name": rs.stop.stop_name,
            "latitude": rs.stop.latitude,
            "longitude": rs.stop.longitude,
            "pickup_time": "08:10:00",
            "student_count": db.query(Student).filter(Student.stop_id == rs.stop.stop_id).count()
        })
    
    return {
        "route_name": f"Route for Bus {coordinator.bus.bus_number}",
        "total_distance_km": route.total_distance,
        "total_duration_minutes": 45,
        "stops": stops
    }

# ─── 4.5 Live Tracking ───────────────────────────────
@router.get("/tracking")
def get_tracking(db: Session = Depends(get_db), coordinator: Coordinator = Depends(verify_coordinator)):
    bus_id = coordinator.bus_id
    is_active = is_bus_active(bus_id)
    location = get_bus_location(bus_id)

    if not is_active or not location:
        return {"bus_id": bus_id, "is_active": False, "status": "parked"}

    location["is_active"] = True
    location["status"] = "active"
    return location

@router.websocket("/ws/tracking/{bus_id}")
async def websocket_tracking(websocket: WebSocket, bus_id: int, token: str = Query(...), db: Session = Depends(get_db)):
    await websocket.accept()
    try:
        coordinator = verify_coordinator(token=token, db=db)
        if coordinator.bus_id != bus_id:
            await websocket.send_text(json.dumps({"error": "Unauthorized bus tracking"}))
            await websocket.close(code=1008)
            return
    except Exception as e:
        await websocket.send_text(json.dumps({"error": str(e)}))
        await websocket.close()
        return

    # Send initial location immediately
    loc = get_bus_location(bus_id)
    if loc:
        loc["is_active"] = True
        await websocket.send_text(json.dumps(loc))
    else:
        await websocket.send_text(json.dumps({"bus_id": bus_id, "is_active": False, "status": "parked"}))

    # Poll loop
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

# ─── 4.6 Announcements ───────────────────────────────
@router.get("/announcements", response_model=List[AnnouncementResponse])
def get_announcements(db: Session = Depends(get_db), coordinator: Coordinator = Depends(verify_coordinator)):
    return db.query(Announcement).filter(
        Announcement.bus_id == coordinator.bus_id,
        Announcement.is_active == True
    ).order_by(Announcement.created_at.desc()).all()

@router.post("/announcements", response_model=AnnouncementResponse)
def create_announcement(announcement: AnnouncementCreate, db: Session = Depends(get_db), coordinator: Coordinator = Depends(verify_coordinator)):
    try:
        # Robust Date Parsing
        import dateutil.parser as parser
        expires_at = None
        try:
            # Use dayfirst=True for Indian format support (DD-MM-YYYY)
            expires_at = parser.parse(announcement.expires_at, dayfirst=True)
        except Exception as date_err:
            print(f"[Announcement Error] dateutil failed: {e if 'e' in locals() else date_err}")
            # Explicit fallbacks for common formats
            date_formats = ["%d-%m-%Y %H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d"]
            for fmt in date_formats:
                try:
                    expires_at = datetime.strptime(announcement.expires_at, fmt)
                    break
                except: continue
        
        if not expires_at:
            expires_at = datetime.now() # Safety fallback
        
        db_ann = Announcement(
            bus_id=coordinator.bus_id,
            coordinator_id=coordinator.id,
            title=announcement.title,
            message=announcement.message,
            expires_at=expires_at
        )
        db.add(db_ann)
        db.commit()
        db.refresh(db_ann)
        return db_ann
    except Exception as e:
        print(f"[Announcement Error] Error saving: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"[Coordinator Post Error] {str(e)}")

@router.delete("/announcements/{id}")
def delete_announcement(id: int, db: Session = Depends(get_db), coordinator: Coordinator = Depends(verify_coordinator)):
    ann = db.query(Announcement).filter(Announcement.id == id, Announcement.bus_id == coordinator.bus_id).first()
    if not ann:
        raise HTTPException(status_code=404, detail="Announcement not found")
    ann.is_active = False
    db.commit()
    return {"message": "Announcement removed"}

# ─── 4.7 Complaints ──────────────────────────────────
@router.get("/complaints", response_model=List[ComplaintResponse])
def get_complaints(status: str = "all", db: Session = Depends(get_db), coordinator: Coordinator = Depends(verify_coordinator)):
    query = db.query(Complaint).filter(Complaint.bus_id == coordinator.bus_id)
    if status in ['open', 'resolved']:
        query = query.filter(Complaint.status == status)
        
    complaints = query.order_by(Complaint.created_at.desc()).all()
    results = []
    for c in complaints:
        student = c.student
        results.append(ComplaintResponse(
            id=c.id,
            student_name=student.name if student else "Unknown",
            roll_number=student.student_id if student else "Unknown",
            category=c.category,
            description=c.description,
            status=c.status,
            created_at=c.created_at.strftime("%Y-%m-%d %H:%M:%S") if c.created_at else "",
            resolution_note=c.resolution_note,
            resolved_at=c.resolved_at.strftime("%Y-%m-%d %H:%M:%S") if c.resolved_at else None
        ))
    return results

@router.put("/complaints/{id}/resolve")
def resolve_complaint(id: int, resolve: ComplaintResolve, db: Session = Depends(get_db), coordinator: Coordinator = Depends(verify_coordinator)):
    complaint = db.query(Complaint).filter(Complaint.id == id, Complaint.bus_id == coordinator.bus_id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    if complaint.status == 'resolved':
        raise HTTPException(status_code=400, detail="Already resolved")
        
    complaint.status = 'resolved'
    complaint.resolution_note = resolve.resolution_note
    complaint.resolved_by = coordinator.id
    complaint.resolved_at = datetime.now()
    db.commit()
    return {"message": "Complaint resolved"}
