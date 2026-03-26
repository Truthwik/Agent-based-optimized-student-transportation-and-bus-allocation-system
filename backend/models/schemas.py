from pydantic import BaseModel
from typing import Optional, List


# ─── Auth ──────────────────────────────────────────
class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    token: str
    role: str
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


# ─── Student ──────────────────────────────────────
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
    reporting_time: str = "7:00 AM"
