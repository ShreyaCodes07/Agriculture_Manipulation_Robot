"""
Router for Sensor Telemetry Readouts
"""

from fastapi import APIRouter
from app.models import SensorData
from app.services.simulator import robot_state

router = APIRouter(prefix="/api", tags=["Sensor Telemetry"])

@router.get("/sensors", response_model=SensorData)
def get_sensor_readings():
    """
    Returns ultrasonic distance (cm) and soil moisture (%) readings.
    """
    return robot_state.sensors
