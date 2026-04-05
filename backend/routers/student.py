from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, List, Any
from datetime import datetime

from ..database import get_db
from ..models.models import Student, Stop, Bus, Allocation, Route, RouteStop, DayPassBooking, BusDailyCapacity
from ..models.schemas import (
    StudentSelectStop, StudentResponse, AllocationResponse, BusPassResponse,
    PassTypeChoice, DayPassAvailableBus, DayPassOrderResponse, DayPassConfirmRequest, DayPassResponse,
    RouteResponse, RouteStopResponse
)
from ..config import RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET, DAY_PASS_FARE
from .auth import decode_token

_rzp_client: Any = None


def _get_razorpay_client():
    global _rzp_client
    if _rzp_client is None:
        try:
            import razorpay
        except ModuleNotFoundError as e:
            raise HTTPException(
                status_code=503,
                detail="Payment SDK not installed. Run: pip install razorpay",
            ) from e
        _rzp_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
    return _rzp_client


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
        raise HTTPException(status_code=401, detail="[Student] Student not found")
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
    # 1. Check for permanent allocation
    allocation = db.query(Allocation).filter(Allocation.student_id == student.student_id).first()
    
    if allocation:
        bus = db.query(Bus).filter(Bus.bus_id == allocation.bus_id).first()
        stop = db.query(Stop).filter(Stop.stop_id == student.stop_id).first()
        
        return AllocationResponse(
            student_id=student.student_id,
            student_name=student.name,
            branch=student.branch,
            year=student.year,
            phone=student.phone,
            stop_name=stop.stop_name if stop else "N/A",
            stop_latitude=stop.latitude if stop else None,
            stop_longitude=stop.longitude if stop else None,
            bus_number=bus.bus_number if bus else "N/A",
            driver_name=bus.driver_name if bus else None,
            driver_phone=bus.driver_phone if bus else None,
        )

    # 2. Check for active Day Pass
    today = datetime.now().strftime("%Y-%m-%d")
    day_pass = db.query(DayPassBooking).filter(
        DayPassBooking.student_id == student.student_id,
        DayPassBooking.booking_date == today,
        DayPassBooking.status == "confirmed"
    ).first()

    if day_pass:
        bus = db.query(Bus).filter(Bus.bus_id == day_pass.bus_id).first()
        stop = db.query(Stop).filter(Stop.stop_id == day_pass.stop_id).first()
        
        return AllocationResponse(
            student_id=student.student_id,
            student_name=student.name,
            branch=student.branch,
            year=student.year,
            phone=student.phone,
            stop_name=stop.stop_name if stop else "N/A",
            stop_latitude=stop.latitude if stop else None,
            stop_longitude=stop.longitude if stop else None,
            bus_number=bus.bus_number if bus else "N/A",
            driver_name=bus.driver_name if bus else None,
            driver_phone=bus.driver_phone if bus else None,
        )

    return None


@router.get("/bus-pass", response_model=Optional[BusPassResponse])
def get_bus_pass(db: Session = Depends(get_db), student: Student = Depends(verify_student)):
    # 1. Check for permanent allocation
    allocation = db.query(Allocation).filter(Allocation.student_id == student.student_id).first()
    
    if allocation:
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

    # 2. Check for active Day Pass
    today = datetime.now().strftime("%Y-%m-%d")
    day_pass = db.query(DayPassBooking).filter(
        DayPassBooking.student_id == student.student_id,
        DayPassBooking.booking_date == today,
        DayPassBooking.status == "confirmed"
    ).first()

    if day_pass:
        bus = db.query(Bus).filter(Bus.bus_id == day_pass.bus_id).first()
        stop = db.query(Stop).filter(Stop.stop_id == day_pass.stop_id).first()
        
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
            reporting_time="7:15 AM (Day Pass)"
        )

    return None


@router.get("/route", response_model=Optional[RouteResponse])
def get_my_route(db: Session = Depends(get_db), student: Student = Depends(verify_student)):
    # Find active bus allocation
    bus_id = student.allocated_bus_id
    if not bus_id:
        # Check Day Pass
        today = datetime.now().strftime("%Y-%m-%d")
        day_pass = db.query(DayPassBooking).filter(
            DayPassBooking.student_id == student.student_id,
            DayPassBooking.booking_date == today,
            DayPassBooking.status == "confirmed"
        ).first()
        if day_pass:
            bus_id = day_pass.bus_id
    
    if not bus_id:
        return None

    route = db.query(Route).filter(Route.bus_id == bus_id).first()
    if not route:
        return None

    stops = []
    for rs in route.route_stops:
        stops.append(RouteStopResponse(
            stop_order=rs.stop_order,
            stop_id=rs.stop.stop_id,
            stop_name=rs.stop.stop_name,
            latitude=rs.stop.latitude,
            longitude=rs.stop.longitude
        ))
    
    return RouteResponse(
        route_id=route.route_id,
        bus_id=route.bus_id,
        bus_number=route.bus.bus_number,
        total_students=route.total_students,
        total_stops=route.total_stops,
        total_distance=getattr(route, 'total_distance', 0.0),
        stops=stops
    )


@router.post("/choose-pass-type")
def choose_pass_type(
    req: PassTypeChoice,
    student: Student = Depends(verify_student),
    db: Session = Depends(get_db)
):
    if student.year != 4:
        raise HTTPException(status_code=400, detail="Only 4th year students can choose pass type")
    student.allocation_type = req.allocation_type
    db.commit()
    return {"message": f"Allocation type set to {req.allocation_type}"}


@router.get("/day-pass/available-buses", response_model=List[DayPassAvailableBus])
def get_available_buses(
    stop_id: int,
    date: str,
    student: Student = Depends(verify_student),
    db: Session = Depends(get_db)
):
    # Find all routes passing through the stop
    route_stops = db.query(RouteStop).filter(RouteStop.stop_id == stop_id).all()
    if not route_stops:
        return []

    available_buses = []
    for rs in route_stops:
        route = db.query(Route).filter(Route.route_id == rs.route_id).first()
        if not route: continue
        bus = db.query(Bus).filter(Bus.bus_id == route.bus_id).first()
        if not bus: continue

        # Count permanent students already allocated to this bus
        permanent_count = db.query(func.count(Student.student_id)).filter(
            Student.allocated_bus_id == bus.bus_id
        ).scalar()

        # Check daily capacity (Day Pass bookings)
        capacity_record = db.query(BusDailyCapacity).filter(
            BusDailyCapacity.bus_id == bus.bus_id,
            BusDailyCapacity.travel_date == date
        ).first()

        day_pass_booked = capacity_record.booked_seats if capacity_record else 0
        available = bus.capacity - (permanent_count + day_pass_booked)

        if available > 0:
            available_buses.append(DayPassAvailableBus(
                bus_id=bus.bus_id,
                bus_number=bus.bus_number,
                route_name=f"Route {route.route_id}",
                available_seats=available
            ))

    return available_buses


@router.post("/day-pass/create-order", response_model=DayPassOrderResponse)
def create_day_pass_order(
    student: Student = Depends(verify_student),
    db: Session = Depends(get_db)
):
    # Check if student already has a confirmed booking for today (YYYY-MM-DD)
    today = datetime.now().strftime("%Y-%m-%d")
    existing = db.query(DayPassBooking).filter(
        DayPassBooking.student_id == student.student_id,
        DayPassBooking.booking_date == today,
        DayPassBooking.status == "confirmed"
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="You already have a confirmed booking for today")

    # Create Razorpay Order
    amount_paise = DAY_PASS_FARE * 100
    rzp = _get_razorpay_client()
    try:
        order = rzp.order.create({
            "amount": amount_paise,
            "currency": "INR",
            "payment_capture": "1"
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Razorpay error: {str(e)}")

    return DayPassOrderResponse(
        order_id=order['id'],
        amount=amount_paise
    )


@router.post("/day-pass/confirm")
def confirm_day_pass(
    req: DayPassConfirmRequest,
    student: Student = Depends(verify_student),
    db: Session = Depends(get_db)
):
    # Verify Signature
    rzp = _get_razorpay_client()
    try:
        rzp.utility.verify_payment_signature({
            'razorpay_order_id': req.razorpay_order_id,
            'razorpay_payment_id': req.razorpay_payment_id,
            'razorpay_signature': req.razorpay_signature
        })
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid payment signature")

    # Atomic Seat Increment & Booking Record
    # We use a transaction for safety
    try:
        # Check capacity including both permanent and day pass students
        bus = db.query(Bus).filter(Bus.bus_id == req.bus_id).first()
        if not bus:
            raise HTTPException(status_code=404, detail="Bus not found")
        permanent_count = db.query(func.count(Student.student_id)).filter(
            Student.allocated_bus_id == req.bus_id
        ).scalar()

        capacity_record = db.query(BusDailyCapacity).filter(
            BusDailyCapacity.bus_id == req.bus_id,
            BusDailyCapacity.travel_date == req.date
        ).with_for_update().first()

        if not capacity_record:
            capacity_record = BusDailyCapacity(bus_id=req.bus_id, travel_date=req.date, booked_seats=0)
            db.add(capacity_record)
            db.flush()
        
        # Reload/lock
        capacity_record = db.query(BusDailyCapacity).filter(
            BusDailyCapacity.bus_id == req.bus_id,
            BusDailyCapacity.travel_date == req.date
        ).with_for_update().first()

        if (capacity_record.booked_seats + permanent_count) >= bus.capacity:
            raise HTTPException(status_code=400, detail="Bus is full")

        capacity_record.booked_seats += 1

        booking = DayPassBooking(
            student_id=student.student_id,
            bus_id=req.bus_id,
            stop_id=req.stop_id,
            booking_date=req.date,
            razorpay_payment_id=req.razorpay_payment_id,
            razorpay_order_id=req.razorpay_order_id,
            status="confirmed",
            created_at=datetime.now().isoformat()
        )
        db.add(booking)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Booking failed: {str(e)}")

    return {"message": "Booking confirmed", "booking_id": booking.id}


@router.get("/day-pass/current", response_model=Optional[DayPassResponse])
def get_current_day_pass(
    student: Student = Depends(verify_student),
    db: Session = Depends(get_db)
):
    today = datetime.now().strftime("%Y-%m-%d")
    booking = db.query(DayPassBooking).filter(
        DayPassBooking.student_id == student.student_id,
        DayPassBooking.booking_date == today,
        DayPassBooking.status == "confirmed"
    ).first()

    if not booking:
        return None

    bus = db.query(Bus).filter(Bus.bus_id == booking.bus_id).first()
    stop = db.query(Stop).filter(Stop.stop_id == booking.stop_id).first()
    route = db.query(Route).filter(Route.bus_id == bus.bus_id).first()

    return DayPassResponse(
        booking_id=booking.id,
        student_name=student.name,
        roll_number=student.student_id,
        bus_number=bus.bus_number,
        route_name=f"Route {route.route_id}" if route else "N/A",
        stop_name=stop.stop_name,
        booking_date=booking.booking_date,
        pickup_time="7:15 AM", # In real app, fetch from RouteStop ETA
        status=booking.status
    )
