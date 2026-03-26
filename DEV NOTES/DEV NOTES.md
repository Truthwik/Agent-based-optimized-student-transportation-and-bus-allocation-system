# BVRIT Smart Bus Management System - Dev Notes

## What's Happening (Current State)
- **Architecture**: We are building a full-stack application using **FastAPI** for the backend, **SQLAlchemy** for database ORM (connecting to **MySQL**), and vanilla **HTML/CSS/JS** for the frontend.
- **Data Models**: Successfully defined database schemas for `Admin`, `Student`, `Bus`, `Stop`, `Route`, `RouteStop`, and `Allocation`.
- **Recent Progress**: 
  - Addressed backend setup errors in `setup_db.py`.
  - Refined the data seeding logic in `seed.py`.
  - Fixed entity properties and removed outdated columns (like the legacy `password_changed` logic) to match the correct DB schema.
- **API Structure**: The backend is cleanly structured with distinct routers (`auth`, `admin`, `student`) and statically serves the frontend application.
- **Core Business Logic**: An optimization engine utilizing **OSRM** (Open Source Routing Machine) is being implemented to calculate the most efficient bus routes based on student stops.

## What's the Plan (Next Steps)
1. **Frontend-Backend Integration**: Wire up the frontend HTML forms/dashboards (Admin Panel, Student View) to correctly consume the new FastAPI endpoints.
2. **Route Optimization Engine Validation**: Validate the OSRM logic to confirm it correctly chains stops and calculates optimal paths without relying on Google Maps.
3. **Allocation Verification**: Further test the bus allocation script (`verify_allocation.py`) to systematically ensure every student requesting a bus is assigned to an optimal route with available seating capacity.
4. **End-to-End Testing**: Run a complete holistic test flow—from an admin setting up buses/stops, to students registering, to final route generation.
