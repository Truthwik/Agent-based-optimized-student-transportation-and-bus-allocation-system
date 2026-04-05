from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
from pathlib import Path

from sqlalchemy.exc import OperationalError

from .database import engine, Base
from .routers import auth, admin, student, driver, tracking

logger = logging.getLogger(__name__)

# Create all tables when DB is reachable (MySQL must be running)
try:
    Base.metadata.create_all(bind=engine)
except Exception as exc:
    logger.warning("Database unavailable at startup — tables not created yet: %s", exc)

app = FastAPI(title="BVRIT Smart Bus Management System", version="1.0.0")


@app.exception_handler(OperationalError)
async def database_operational_error_handler(request: Request, exc: OperationalError):
    """Return JSON instead of HTML when MySQL is down or misconfigured (login/API use DB)."""
    logger.warning("Database operational error on %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=503,
        content={
            "detail": "Database unavailable. Start MySQL (e.g. Windows service MYSQL80), then restart Uvicorn. Check .env DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME."
        },
    )

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(student.router)
app.include_router(driver.router)
app.include_router(tracking.router)

# Serve frontend static files
frontend_path = Path(__file__).resolve().parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")


@app.get("/")
def root():
    """Redirect to student login page."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/static/html/login.html")


@app.get("/health")
def health():
    return {"status": "ok", "app": "BVRIT Smart Bus Management System"}
