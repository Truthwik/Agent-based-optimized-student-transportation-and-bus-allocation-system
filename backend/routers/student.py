from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import Optional

from ..database import get_db
from ..models.models import Student, Stop, Bus, Allocation
from ..models.schemas import StudentSelectStop, StudentResponse, AllocationResponse, BusPassResponse
from .auth import decode_token

router = APIRouter(prefix="/students", tags=["Students"])


def verify_student(authorization: str = Header(...), db: Session = Depends(get_db)):
    """Verify student from Authorization header."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    token = authorization.split(" ")[1]
    payload = decode_token(token)
    if payload.get("role") != "student":
        raise HTTPException(status_code=403, detail="Student access required")
    student = db.query(Student).filter(Student.student_id == payload.get("sub")).first()
    if not student:
        raise HTTPException(status_code=401, detail="Student not found")
    return student


@router.get("/me", response_model=StudentResponse)
def get_profile(student: Student = Depends(verify_student)):
    return student


@router.get("/stops")
def get_available_stops(db: Session = Depends(get_db), student: Student = Depends(verify_student)):
    stops = db.query(Stop).all()
    return [{"stop_id": s.stop_id, "stop_name": s.stop_name, "latitude": s.latitude, "longitude": s.longitude} for s in stops]


@router.post("/select-stop")
def select_stop(req: StudentSelectStop, db: Session = Depends(get_db), student: Student = Depends(verify_student)):
    student.bus_required = req.bus_required

    if req.bus_required:
        if not req.stop_id:
            raise HTTPException(status_code=400, detail="Stop ID is required when bus service is selected")
        stop = db.query(Stop).filter(Stop.stop_id == req.stop_id).first()
        if not stop:
            raise HTTPException(status_code=404, detail="Stop not found")
        student.stop_id = req.stop_id
    else:
        student.stop_id = None

    db.commit()
    db.refresh(student)
    return {"message": "Selection saved successfully", "bus_required": student.bus_required, "stop_id": student.stop_id}


@router.get("/allocation", response_model=Optional[AllocationResponse])
def get_allocation(db: Session = Depends(get_db), student: Student = Depends(verify_student)):
    allocation = db.query(Allocation).filter(Allocation.student_id == student.student_id).first()
    if not allocation:
        return None

    bus = db.query(Bus).filter(Bus.bus_id == allocation.bus_id).first()
    stop = db.query(Stop).filter(Stop.stop_id == student.stop_id).first()

    return AllocationResponse(
        student_id=student.student_id,
        student_name=student.name,
        branch=student.branch,
        year=student.year,
        phone=student.phone,
        stop_name=stop.stop_name if stop else "N/A",
        bus_number=bus.bus_number if bus else "N/A",
        driver_name=bus.driver_name if bus else None,
        driver_phone=bus.driver_phone if bus else None,
    )


@router.get("/bus-pass", response_model=Optional[BusPassResponse])
def get_bus_pass(db: Session = Depends(get_db), student: Student = Depends(verify_student)):
    allocation = db.query(Allocation).filter(Allocation.student_id == student.student_id).first()
    if not allocation:
        return None

    bus = db.query(Bus).filter(Bus.bus_id == allocation.bus_id).first()
    stop = db.query(Stop).filter(Stop.stop_id == student.stop_id).first()

    return BusPassResponse(
        student_name=student.name,
        roll_number=student.student_id,
        phone=student.phone,
        branch=student.branch,
        year=student.year,
        pickup_stop=stop.stop_name if stop else "N/A",
        bus_number=bus.bus_number if bus else "N/A",
        driver_name=bus.driver_name if bus else None,
        driver_phone=bus.driver_phone if bus else None,
        reporting_time="7:00 AM"
    )
