from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import jwt
from datetime import datetime, timedelta

from ..database import get_db
from ..models.models import Admin, Student
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


def get_current_user(token: str, db: Session):
    """Extract user from Bearer token."""
    payload = decode_token(token)
    role = payload.get("role")
    user_id = payload.get("sub")

    if role == "admin":
        user = db.query(Admin).filter(Admin.username == user_id).first()
    elif role == "student":
        user = db.query(Student).filter(Student.student_id == user_id).first()
    else:
        raise HTTPException(status_code=401, detail="Invalid role")

    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user, role


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

    raise HTTPException(status_code=401, detail="Invalid ID or Password")


@router.post("/change-password")
def change_password(
    req: ChangePasswordRequest,
    token: str = "",
    db: Session = Depends(get_db)
):
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
    else:
        raise HTTPException(status_code=401, detail="[Auth] Invalid role")

    if user.password != req.old_password:
        raise HTTPException(status_code=400, detail="[Auth] Current password is incorrect")

    user.password = req.new_password
    db.commit()
    return {"message": "Password changed successfully"}
