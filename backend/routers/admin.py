from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import List

from backend.database import get_db
from backend.models.models import Admin, Stop, Bus, Student, Route, RouteStop, Allocation
from backend.models.schemas import (
    StopCreate, StopUpdate, StopResponse,
    BusCreate, BusUpdate, BusResponse,
    StudentResponse, RouteResponse, RouteStopResponse
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
