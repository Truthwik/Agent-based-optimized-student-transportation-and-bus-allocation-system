from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

from .database import engine, Base
from .routers import auth, admin, student

# Create all tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="BVRIT Smart Bus Management System", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(student.router)

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
