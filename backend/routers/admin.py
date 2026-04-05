from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from datetime import datetime

from backend.database import get_db
from backend.models.models import Admin, Stop, Bus, Student, Route, RouteStop, Allocation, Coordinator, Announcement
from backend.models.schemas import (
    StopCreate, StopUpdate, StopResponse,
    BusCreate, BusUpdate, BusResponse,
    StudentResponse, RouteResponse, RouteStopResponse,
    CoordinatorCreate, CoordinatorUpdate, CoordinatorResponse,
    AnnouncementCreate, AnnouncementResponse
)
from backend.routers.auth import decode_token

router = APIRouter(prefix="/admin", tags=["Admin"])


def verify_admin(authorization: str = Header(...), db: Session = Depends(get_db)):
    """Verify admin from Authorization header."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    token = authorization.split(" ")[1]
    payload = decode_token(token)
    if payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    admin = db.query(Admin).filter(Admin.username == payload.get("sub")).first()
    if not admin:
        raise HTTPException(status_code=401, detail="[Admin] Admin not found")
    return admin


# ─── STOPS CRUD ────────────────────────────────────
@router.get("/stops", response_model=List[StopResponse])
def get_stops(db: Session = Depends(get_db), admin=Depends(verify_admin)):
    return db.query(Stop).all()


@router.post("/stops", response_model=StopResponse)
def create_stop(stop: StopCreate, db: Session = Depends(get_db), admin=Depends(verify_admin)):
    db_stop = Stop(**stop.model_dump())
    db.add(db_stop)
    db.commit()
    db.refresh(db_stop)
    return db_stop


@router.put("/stops/{stop_id}", response_model=StopResponse)
def update_stop(stop_id: int, stop: StopUpdate, db: Session = Depends(get_db), admin=Depends(verify_admin)):
    db_stop = db.query(Stop).filter(Stop.stop_id == stop_id).first()
    if not db_stop:
        raise HTTPException(status_code=404, detail="Stop not found")
    for key, value in stop.model_dump(exclude_unset=True).items():
        setattr(db_stop, key, value)
    db.commit()
    db.refresh(db_stop)
    return db_stop


@router.delete("/stops/{stop_id}")
def delete_stop(stop_id: int, db: Session = Depends(get_db), admin=Depends(verify_admin)):
    db_stop = db.query(Stop).filter(Stop.stop_id == stop_id).first()
    if not db_stop:
        raise HTTPException(status_code=404, detail="Stop not found")
    # Check if students are using this stop
    students_using = db.query(Student).filter(Student.stop_id == stop_id).count()
    if students_using > 0:
        raise HTTPException(status_code=400, detail=f"{students_using} students are assigned to this stop. Reassign them first.")
    db.delete(db_stop)
    db.commit()
    return {"message": "Stop deleted successfully"}


# ─── BUSES CRUD ────────────────────────────────────
@router.get("/buses", response_model=List[BusResponse])
def get_buses(db: Session = Depends(get_db), admin=Depends(verify_admin)):
    return db.query(Bus).all()


@router.post("/buses", response_model=BusResponse)
def create_bus(bus: BusCreate, db: Session = Depends(get_db), admin=Depends(verify_admin)):
    existing = db.query(Bus).filter(Bus.bus_number == bus.bus_number).first()
    if existing:
        raise HTTPException(status_code=400, detail="Bus number already exists")
    db_bus = Bus(**bus.model_dump())
    db.add(db_bus)
    db.commit()
    db.refresh(db_bus)
    return db_bus


@router.put("/buses/{bus_id}", response_model=BusResponse)
def update_bus(bus_id: int, bus: BusUpdate, db: Session = Depends(get_db), admin=Depends(verify_admin)):
    db_bus = db.query(Bus).filter(Bus.bus_id == bus_id).first()
    if not db_bus:
        raise HTTPException(status_code=404, detail="Bus not found")
    for key, value in bus.model_dump(exclude_unset=True).items():
        setattr(db_bus, key, value)
    db.commit()
    db.refresh(db_bus)
    return db_bus


@router.delete("/buses/{bus_id}")
def delete_bus(bus_id: int, db: Session = Depends(get_db), admin=Depends(verify_admin)):
    db_bus = db.query(Bus).filter(Bus.bus_id == bus_id).first()
    if not db_bus:
        raise HTTPException(status_code=404, detail="Bus not found")
    db.delete(db_bus)
    db.commit()
    return {"message": "Bus deleted successfully"}


# ─── STUDENTS ─────────────────────────────────────
@router.get("/students", response_model=List[StudentResponse])
def get_students(db: Session = Depends(get_db), admin=Depends(verify_admin)):
    return db.query(Student).all()


# ─── GENERATE ALLOCATION ──────────────────────────
@router.post("/generate-allocation")
def generate_allocation(db: Session = Depends(get_db), admin=Depends(verify_admin)):
    from backend.services.optimizer_engine import run_optimizer
    result = run_optimizer(db)
    return result


# ─── ROUTES ───────────────────────────────────────
@router.get("/routes", response_model=List[RouteResponse])
def get_routes(db: Session = Depends(get_db), admin=Depends(verify_admin)):
    routes = db.query(Route).all()
    result = []
    for route in routes:
        stops = []
        for rs in route.route_stops:
            stops.append(RouteStopResponse(
                stop_order=rs.stop_order,
                stop_id=rs.stop.stop_id,
                stop_name=rs.stop.stop_name,
                latitude=rs.stop.latitude,
                longitude=rs.stop.longitude
            ))
        result.append(RouteResponse(
            route_id=route.route_id,
            bus_id=route.bus_id,
            bus_number=route.bus.bus_number,
            total_students=route.total_students,
            total_stops=route.total_stops,
            total_distance=getattr(route, 'total_distance', 0.0),
            stops=stops
        ))
    return result


# ─── ALLOCATIONS ──────────────────────────────────
@router.get("/allocations")
def get_allocations(db: Session = Depends(get_db), admin=Depends(verify_admin)):
    allocations = db.query(Allocation).all()
    result = []
    for alloc in allocations:
        student = alloc.student
        bus = alloc.bus
        stop = student.stop
        result.append({
            "allocation_id": alloc.allocation_id,
            "student_id": student.student_id,
            "student_name": student.name,
            "branch": student.branch,
            "year": student.year,
            "stop_name": stop.stop_name if stop else "N/A",
            "bus_number": bus.bus_number,
            "academic_year": alloc.academic_year,
        })
    return result


# ─── COORDINATORS ─────────────────────────────────
@router.get("/coordinators", response_model=List[CoordinatorResponse])
def get_coordinators(db: Session = Depends(get_db), admin=Depends(verify_admin)):
    coordinators = db.query(Coordinator).all()
    # Populate bus_number for response
    for c in coordinators:
        if c.bus:
            c.bus_number = c.bus.bus_number
    return coordinators


@router.post("/coordinators", response_model=CoordinatorResponse)
def create_coordinator(coordinator: CoordinatorCreate, db: Session = Depends(get_db), admin=Depends(verify_admin)):
    # Check if employee_id or email already exists
    if db.query(Coordinator).filter((Coordinator.employee_id == coordinator.employee_id) | (Coordinator.email == coordinator.email)).first():
        raise HTTPException(status_code=400, detail="Employee ID or Email already exists")
    
    # Check if bus is already assigned to a coordinator
    if db.query(Coordinator).filter(Coordinator.bus_id == coordinator.bus_id).first():
        raise HTTPException(status_code=400, detail="This bus is already assigned to another coordinator")

    # Create new coordinator with default password = employee_id
    db_coord = Coordinator(
        name=coordinator.name,
        employee_id=coordinator.employee_id,
        email=coordinator.email,
        phone=coordinator.phone,
        bus_id=coordinator.bus_id,
        password_hash=coordinator.employee_id,  # Default password
        password_changed=False,
        is_active=True
    )
    db.add(db_coord)
    db.commit()
    db.refresh(db_coord)
    if db_coord.bus:
        db_coord.bus_number = db_coord.bus.bus_number
    return db_coord


@router.put("/coordinators/{id}", response_model=CoordinatorResponse)
def update_coordinator(id: int, coordinator: CoordinatorUpdate, db: Session = Depends(get_db), admin=Depends(verify_admin)):
    db_coord = db.query(Coordinator).filter(Coordinator.id == id).first()
    if not db_coord:
        raise HTTPException(status_code=404, detail="Coordinator not found")
    
    if coordinator.bus_id is not None and coordinator.bus_id != db_coord.bus_id:
        # Check if new bus is already assigned to *another* coordinator
        if db.query(Coordinator).filter((Coordinator.bus_id == coordinator.bus_id) & (Coordinator.id != id)).first():
            raise HTTPException(status_code=400, detail="This bus is already assigned to another coordinator")

    for key, value in coordinator.model_dump(exclude_unset=True).items():
        setattr(db_coord, key, value)
        
    db.commit()
    db.refresh(db_coord)
    if db_coord.bus:
        db_coord.bus_number = db_coord.bus.bus_number
    return db_coord


@router.delete("/coordinators/{id}")
def delete_coordinator(id: int, db: Session = Depends(get_db), admin=Depends(verify_admin)):
    db_coord = db.query(Coordinator).filter(Coordinator.id == id).first()
    if not db_coord:
        raise HTTPException(status_code=404, detail="Coordinator not found")
    
    # Soft delete
    db_coord.is_active = False
    db.commit()
    return {"message": "Coordinator deactivated successfully"}


# ─── STOP CHANGE REQUESTS ─────────────────────────
from ..models.models import StopChangeRequest, RouteStop, Route, Allocation

@router.get("/stop-change-requests")
def get_stop_change_requests(db: Session = Depends(get_db), admin=Depends(verify_admin)):
    requests = db.query(StopChangeRequest).all()
    results = []
    
    for req in requests:
        # Determine projected bus
        projected_bus = None
        projected_capacity = None
        projected_allocated = None
        route_stop = db.query(RouteStop).filter(RouteStop.stop_id == req.requested_stop_id).first()
        if route_stop:
            route = db.query(Route).filter(Route.route_id == route_stop.route_id).first()
            if route and route.bus:
                projected_bus = route.bus.bus_number
                projected_capacity = route.bus.capacity
                projected_allocated = route.total_students

        results.append({
            "id": req.id,
            "student_id": req.student_id,
            "student_name": req.student.name if req.student else "Unknown",
            "current_stop_name": req.current_stop.stop_name if req.current_stop else "Unknown",
            "requested_stop_name": req.requested_stop.stop_name if req.requested_stop else "Unknown",
            "requested_stop_id": req.requested_stop_id,
            "reason": req.reason,
            "status": req.status,
            "created_at": str(req.created_at),
            "projected_bus_number": projected_bus,
            "projected_bus_capacity": projected_capacity,
            "projected_bus_allocated": projected_allocated,
            "resolved_at": str(req.resolved_at) if req.resolved_at else None
        })
    # Sort pending first
    results.sort(key=lambda x: (x["status"] != "pending", x["created_at"]), reverse=True)
    return results

@router.post("/stop-change-requests/{id}/approve")
def approve_stop_change(id: int, db: Session = Depends(get_db), admin=Depends(verify_admin)):
    req = db.query(StopChangeRequest).filter(StopChangeRequest.id == id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    if req.status != "pending":
        raise HTTPException(status_code=400, detail="Request is already resolved")

    # Find the new bus
    route_stop = db.query(RouteStop).filter(RouteStop.stop_id == req.requested_stop_id).first()
    if not route_stop:
        raise HTTPException(status_code=400, detail="No bus route currently services the requested stop.")
    
    new_route = db.query(Route).filter(Route.route_id == route_stop.route_id).first()
    new_bus_id = new_route.bus_id

    # Find current allocation
    allocation = db.query(Allocation).filter(Allocation.student_id == req.student_id).first()
    if allocation:
        old_bus_id = allocation.bus_id
        # Decrement old route
        old_route = db.query(Route).filter(Route.bus_id == old_bus_id).first()
        if old_route and old_route.total_students > 0:
            old_route.total_students -= 1
        
        # Update allocation
        allocation.bus_id = new_bus_id

        # Increment new route
        new_route.total_students += 1
    
    # Update student stop and allocated bus
    if req.student:
        req.student.stop_id = req.requested_stop_id
        req.student.allocated_bus_id = new_bus_id

    # Resolve request
    req.status = "approved"
    req.resolved_at = func.now()
    
    db.commit()
    return {"message": "Request approved and student reallocated."}

@router.post("/stop-change-requests/{id}/reject")
def reject_stop_change(id: int, db: Session = Depends(get_db), admin=Depends(verify_admin)):
    req = db.query(StopChangeRequest).filter(StopChangeRequest.id == id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    if req.status != "pending":
        raise HTTPException(status_code=400, detail="Request is already resolved")

    req.status = "rejected"
    req.resolved_at = func.now()
    db.commit()
    return {"message": "Request rejected."}
    
# ─── ANNOUNCEMENTS ────────────────────────────────
@router.get("/announcements", response_model=List[AnnouncementResponse])
def get_admin_announcements(db: Session = Depends(get_db), admin=Depends(verify_admin)):
    return db.query(Announcement).filter(
        Announcement.is_active == True
    ).order_by(Announcement.created_at.desc()).all()

@router.post("/announcements", response_model=AnnouncementResponse)
def create_admin_announcement(announcement: AnnouncementCreate, db: Session = Depends(get_db), admin=Depends(verify_admin)):
    try:
        import dateutil.parser as parser
        expires_at = None
        try:
            expires_at = parser.parse(announcement.expires_at, dayfirst=True)
        except Exception as date_err:
            print(f"dateutil parse failed: {date_err}")
            date_formats = ["%d-%m-%Y %H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d"]
            for fmt in date_formats:
                try:
                    expires_at = datetime.strptime(announcement.expires_at, fmt)
                    break
                except: continue
        
        if not expires_at:
            expires_at = datetime.now() # Safety fallback
            
        db_ann = Announcement(
            bus_id=None,
            coordinator_id=None,
            title=announcement.title,
            message=announcement.message,
            expires_at=expires_at
        )
        db.add(db_ann)
        db.commit()
        db.refresh(db_ann)
        return db_ann
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"[Admin Post Error] {str(e)}")

@router.delete("/announcements/{id}")
def delete_admin_announcement(id: int, db: Session = Depends(get_db), admin=Depends(verify_admin)):
    ann = db.query(Announcement).filter(Announcement.id == id).first()
    if not ann:
        raise HTTPException(status_code=404, detail="Announcement not found")
    ann.is_active = False
    db.commit()
    return {"message": "Announcement deleted"}
