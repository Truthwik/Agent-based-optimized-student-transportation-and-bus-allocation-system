from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
import jwt
from datetime import datetime, timedelta

from ..database import get_db
from ..models.models import Admin, Student, Bus, Coordinator
from ..models.schemas import LoginRequest, LoginResponse, ChangePasswordRequest
from ..config import JWT_SECRET, JWT_ALGORITHM

router = APIRouter(prefix="/auth", tags=["Auth"])


def create_token(data: dict, expires_hours: int = 24) -> str:
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(hours=expires_hours)
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


@router.post("/login", response_model=LoginResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    # Try admin login
    admin = db.query(Admin).filter(Admin.username == req.username).first()
    if admin and admin.password == req.password:
        token = create_token({"sub": admin.username, "role": "admin"})
        return LoginResponse(
            token=token,
            role="admin",
            password_changed=(admin.password != admin.username)
        )

    # Try student login
    student = db.query(Student).filter(Student.student_id == req.username).first()
    if student and student.password == req.password:
        token = create_token({"sub": student.student_id, "role": "student"})
        return LoginResponse(
            token=token,
            role="student",
            password_changed=(student.password != student.student_id)
        )

    # Try driver login
    bus = db.query(Bus).filter(Bus.bus_number == req.username).first()
    if bus and bus.driver_phone == req.password:
        token = create_token({"sub": bus.bus_number, "role": "driver", "bus_id": bus.bus_id})
        return LoginResponse(
            token=token,
            role="driver",
            bus_id=bus.bus_id,
            password_changed=True
        )

    # Try coordinator login
    coordinator = db.query(Coordinator).filter(Coordinator.employee_id == req.username).first()
    if coordinator and coordinator.password_hash == req.password:
        if not coordinator.is_active:
            raise HTTPException(status_code=403, detail="Account deactivated by admin.")
        token = create_token({"sub": coordinator.employee_id, "role": "coordinator", "bus_id": coordinator.bus_id})
        return LoginResponse(
            token=token,
            role="coordinator",
            bus_id=coordinator.bus_id,
            password_changed=coordinator.password_changed
        )

    raise HTTPException(status_code=401, detail="Invalid ID or Password")


@router.get("/debug/buses")
def debug_buses(db: Session = Depends(get_db)):
    """Temporary debug endpoint — shows bus_number and driver_phone for testing."""
    buses = db.query(Bus).all()
    return [{"bus_id": b.bus_id, "bus_number": b.bus_number, "driver_phone": b.driver_phone} for b in buses]


@router.post("/change-password")
def change_password(
    req: ChangePasswordRequest,
    authorization: str = Header(..., alias="Authorization"),
    db: Session = Depends(get_db),
):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    token = authorization.split(" ", 1)[1].strip()
    payload = decode_token(token)
    user_id = payload.get("sub")
    role = payload.get("role")

    if role == "admin":
        user = db.query(Admin).filter(Admin.username == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="[Auth] Admin account not found")
    elif role == "student":
        user = db.query(Student).filter(Student.student_id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="[Auth] Student account not found")
    elif role == "driver":
        user = db.query(Bus).filter(Bus.bus_number == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="[Auth] Driver/bus not found")
        if user.driver_phone != req.old_password:
            raise HTTPException(status_code=400, detail="[Auth] Current password is incorrect")
        user.driver_phone = req.new_password
        db.commit()
        return {"message": "Password changed successfully"}
    elif role == "coordinator":
        user = db.query(Coordinator).filter(Coordinator.employee_id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="[Auth] Coordinator not found")
        if user.password_hash != req.old_password:
            raise HTTPException(status_code=400, detail="[Auth] Current password is incorrect")
        user.password_hash = req.new_password
        user.password_changed = True
        db.commit()
        return {"message": "Password changed successfully"}
    else:
        raise HTTPException(status_code=401, detail="[Auth] Invalid role")

    if user.password != req.old_password:
        raise HTTPException(status_code=400, detail="[Auth] Current password is incorrect")

    user.password = req.new_password
    db.commit()
    return {"message": "Password changed successfully"}
