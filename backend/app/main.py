"""
Agriculture Manipulation Robot - FastAPI Core Application Entrypoint
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.database import init_db
from app.services.simulator import robot_state
from app.models import RobotStatusResponse
from app.routers import control, sensors, logs, simulation, vision, mission, arm

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize Database & Seed initial records
    init_db()
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Full-stack simulation-first API for Agriculture Manipulation Robot control, OpenCV vision, and field telemetry monitoring.",
    lifespan=lifespan
)

# CORS Middleware Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(control.router)
app.include_router(sensors.router)
app.include_router(logs.router)
app.include_router(simulation.router)
app.include_router(vision.router)
app.include_router(mission.router)
app.include_router(arm.router)




import os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

frontend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend"))
index_file = os.path.join(frontend_path, "index.html")

@app.get("/api", tags=["Health Check"])
@app.get("/api/info", tags=["Health Check"])
def root_status():
    """
    Root API welcome and system information route.
    """
    return {
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "mode": settings.MODE,
        "status": "ONLINE",
        "docs_url": "/docs"
    }

@app.get("/api/health", tags=["Health Check"])
def health_check():
    """
    Backend Health Check Endpoint.
    """
    return {
        "status": "healthy",
        "mode": settings.MODE,
        "estop": robot_state.estop_engaged
    }

@app.get("/api/status", response_model=RobotStatusResponse, tags=["Robot Status"])
def get_robot_status():
    """
    Returns full current robot status (pose, arm angles, gripper state, sensors, e-stop, and mode).
    """
    return robot_state.get_status()

@app.get("/", tags=["Frontend"])
def serve_index():
    """
    Serves the primary Single Page Application (SPA) dashboard.
    """
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return root_status()

# Serve static frontend web assets (CSS, JS)
if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")

