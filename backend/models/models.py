from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from backend.database import Base


class Admin(Base):
    __tablename__ = "admins"

    admin_id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    password = Column(String(255), nullable=False)


class Stop(Base):
    __tablename__ = "stops"

    stop_id = Column(Integer, primary_key=True, autoincrement=True)
    stop_name = Column(String(100), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)

    students = relationship("Student", back_populates="stop")
    route_stops = relationship("RouteStop", back_populates="stop")


class Bus(Base):
    __tablename__ = "buses"

    bus_id = Column(Integer, primary_key=True, autoincrement=True)
    bus_number = Column(String(20), unique=True, nullable=False)
    capacity = Column(Integer, nullable=False, default=50)
    driver_name = Column(String(100), nullable=True)
    driver_phone = Column(String(15), nullable=True)

    students = relationship("Student", back_populates="allocated_bus")
    routes = relationship("Route", back_populates="bus")
    allocations = relationship("Allocation", back_populates="bus")


class Student(Base):
    __tablename__ = "students"

    student_id = Column(String(20), primary_key=True)
    name = Column(String(100), nullable=False)
    branch = Column(String(50), nullable=False)
    year = Column(Integer, nullable=False)
    phone = Column(String(15), nullable=True)
    password = Column(String(255), nullable=False)
    bus_required = Column(Boolean, default=False)
    stop_id = Column(Integer, ForeignKey("stops.stop_id"), nullable=True)
    allocated_bus_id = Column(Integer, ForeignKey("buses.bus_id"), nullable=True)
    allocation_type = Column(String(20), nullable=True)  # 'yearwise', 'daywise', or NULL

    stop = relationship("Stop", back_populates="students")
    allocated_bus = relationship("Bus", back_populates="students")
    allocations = relationship("Allocation", back_populates="student")
    day_passes = relationship("DayPassBooking", back_populates="student")


class Route(Base):
    __tablename__ = "routes"

    route_id = Column(Integer, primary_key=True, autoincrement=True)
    bus_id = Column(Integer, ForeignKey("buses.bus_id"), nullable=False)
    total_students = Column(Integer, default=0)
    total_stops = Column(Integer, default=0)
    total_distance = Column(Float, default=0.0)

    bus = relationship("Bus", back_populates="routes")
    route_stops = relationship("RouteStop", back_populates="route", order_by="RouteStop.stop_order")


class RouteStop(Base):
    __tablename__ = "route_stops"

    route_stop_id = Column(Integer, primary_key=True, autoincrement=True)
    route_id = Column(Integer, ForeignKey("routes.route_id"), nullable=False)
    stop_id = Column(Integer, ForeignKey("stops.stop_id"), nullable=False)
    stop_order = Column(Integer, nullable=False)

    route = relationship("Route", back_populates="route_stops")
    stop = relationship("Stop", back_populates="route_stops")


class Allocation(Base):
    __tablename__ = "allocations"

    allocation_id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(String(20), ForeignKey("students.student_id"), nullable=False)
    bus_id = Column(Integer, ForeignKey("buses.bus_id"), nullable=False)
    academic_year = Column(String(20), nullable=False)

    student = relationship("Student", back_populates="allocations")
    bus = relationship("Bus", back_populates="allocations")


class DayPassBooking(Base):
    __tablename__ = "day_pass_bookings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(String(20), ForeignKey("students.student_id"), nullable=False)
    bus_id = Column(Integer, ForeignKey("buses.bus_id"), nullable=False)
    stop_id = Column(Integer, ForeignKey("stops.stop_id"), nullable=False)
    booking_date = Column(String(10), nullable=False)  # YYYY-MM-DD
    razorpay_payment_id = Column(String(100), nullable=True)
    razorpay_order_id = Column(String(100), nullable=True)
    status = Column(String(20), default="pending")  # 'pending', 'confirmed', 'failed'
    created_at = Column(String(30), nullable=True)

    student = relationship("Student", back_populates="day_passes")


class BusDailyCapacity(Base):
    __tablename__ = "bus_daily_capacity"

    id = Column(Integer, primary_key=True, autoincrement=True)
    bus_id = Column(Integer, ForeignKey("buses.bus_id"), nullable=False)
    travel_date = Column(String(10), nullable=False)  # YYYY-MM-DD
    booked_seats = Column(Integer, default=0)
