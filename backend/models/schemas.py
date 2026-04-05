from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


# ─── Auth ──────────────────────────────────────────
class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    token: str
    role: str
    bus_id: Optional[int] = None
    password_changed: Optional[bool] = None

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


# ─── Stop ──────────────────────────────────────────
class StopCreate(BaseModel):
    stop_name: str
    latitude: float
    longitude: float

class StopUpdate(BaseModel):
    stop_name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class StopResponse(BaseModel):
    stop_id: int
    stop_name: str
    latitude: float
    longitude: float

    class Config:
        from_attributes = True


# ─── Bus ───────────────────────────────────────────
class BusCreate(BaseModel):
    bus_number: str
    capacity: int = 50
    driver_name: Optional[str] = None
    driver_phone: Optional[str] = None

class BusUpdate(BaseModel):
    bus_number: Optional[str] = None
    capacity: Optional[int] = None
    driver_name: Optional[str] = None
    driver_phone: Optional[str] = None

class BusResponse(BaseModel):
    bus_id: int
    bus_number: str
    capacity: int
    driver_name: Optional[str] = None
    driver_phone: Optional[str] = None

    class Config:
        from_attributes = True


class PassTypeChoice(BaseModel):
    allocation_type: str  # 'yearwise' or 'daywise'

class DayPassAvailableBus(BaseModel):
    bus_id: int
    bus_number: str
    route_name: str
    available_seats: int
    pickup_time: Optional[str] = None  # scheduled departure at chosen stop, if known

class DayPassOrderResponse(BaseModel):
    order_id: str
    amount: int
    currency: str = "INR"

class DayPassConfirmRequest(BaseModel):
    razorpay_payment_id: str
    razorpay_order_id: str
    razorpay_signature: str
    stop_id: int
    bus_id: int
    date: str

class DayPassResponse(BaseModel):
    booking_id: int
    student_name: str
    roll_number: str
    bus_number: str
    route_name: str
    stop_name: str
    booking_date: str
    pickup_time: str
    status: str

    class Config:
        from_attributes = True

class StudentSelectStop(BaseModel):
    bus_required: bool
    stop_id: Optional[int] = None

class StudentResponse(BaseModel):
    student_id: str
    name: str
    branch: str
    year: int
    phone: Optional[str] = None
    bus_required: bool
    stop_id: Optional[int] = None
    allocated_bus_id: Optional[int] = None
    allocated_bus_number: Optional[str] = None
    allocation_type: Optional[str] = None

    class Config:
        from_attributes = True


# ─── Allocation ───────────────────────────────────
class AllocationResponse(BaseModel):
    student_id: str
    student_name: str
    branch: str
    year: int
    phone: Optional[str] = None
    stop_name: str
    stop_latitude: Optional[float] = None
    stop_longitude: Optional[float] = None
    bus_number: str
    driver_name: Optional[str] = None
    driver_phone: Optional[str] = None

    class Config:
        from_attributes = True


# ─── Route ─────────────────────────────────────────
class RouteStopResponse(BaseModel):
    stop_order: int
    stop_id: int
    stop_name: str
    latitude: float
    longitude: float
    scheduled_departure: Optional[str] = None

    class Config:
        from_attributes = True

class RouteResponse(BaseModel):
    route_id: int
    bus_id: int
    bus_number: str
    total_students: int
    total_stops: int
    total_distance: float = 0.0
    stops: List[RouteStopResponse] = []

    class Config:
        from_attributes = True


# ─── Bus Pass ──────────────────────────────────────
class BusPassResponse(BaseModel):
    student_name: str
    roll_number: str
    phone: Optional[str] = None
    branch: str
    year: int
    pickup_stop: str
    bus_number: str
    driver_name: Optional[str] = None
    driver_phone: Optional[str] = None
    reporting_time: str


# ─── Coordinator ───────────────────────────────────
class CoordinatorCreate(BaseModel):
    name: str
    employee_id: str
    email: str
    phone: str
    bus_id: int

class CoordinatorUpdate(BaseModel):
    name: Optional[str] = None
    employee_id: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    bus_id: Optional[int] = None
    is_active: Optional[bool] = None

class CoordinatorResponse(BaseModel):
    id: int
    name: str
    employee_id: str
    email: str
    phone: str
    bus_id: int
    bus_number: Optional[str] = None
    is_active: bool

    class Config:
        from_attributes = True

# ─── Announcement ──────────────────────────────────
class AnnouncementCreate(BaseModel):
    title: str
    message: str
    expires_at: str

class AnnouncementResponse(BaseModel):
    id: int
    title: str
    message: str
    created_at: datetime
    expires_at: datetime
    is_active: bool
    bus_id: Optional[int] = None

    class Config:
        from_attributes = True

# ─── Complaint ─────────────────────────────────────
class ComplaintCreate(BaseModel):
    category: str
    description: str

class ComplaintResolve(BaseModel):
    resolution_note: str

class ComplaintResponse(BaseModel):
    id: int
    student_name: str
    roll_number: str
    category: str
    description: str
    status: str
    created_at: str
    resolution_note: Optional[str] = None
    resolved_at: Optional[str] = None

    class Config:
        from_attributes = True

# ─── Coordinator Dashboard ─────────────────────────
class CoordinatorDashboardBus(BaseModel):
    bus_number: str
    max_capacity: int
    driver_name: Optional[str] = None
    driver_phone: Optional[str] = None

class CoordinatorDashboardSummary(BaseModel):
    total_students_allocated: int
    yearwise_students: int
    daypass_students_today: int
    available_seats: int
    occupancy_percent: int
    bus_is_live: bool
    open_complaints: int
    active_announcements: int

class CoordinatorDashboardResponse(BaseModel):
    coordinator: CoordinatorResponse
    bus: CoordinatorDashboardBus
    summary: CoordinatorDashboardSummary

# ─── Stop Change Request ───────────────────────────
class StopChangeRequestCreate(BaseModel):
    requested_stop_id: int
    reason: str

class StopChangeRequestResponse(BaseModel):
    id: int
    student_id: str
    student_name: str
    current_stop_name: str
    requested_stop_name: str
    requested_stop_id: int
    reason: str
    status: str
    created_at: str
    projected_bus_number: Optional[str] = None
    projected_bus_capacity: Optional[int] = None
    projected_bus_allocated: Optional[int] = None
    resolved_at: Optional[str] = None

    class Config:
        from_attributes = True
