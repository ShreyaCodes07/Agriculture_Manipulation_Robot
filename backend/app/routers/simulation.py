"""
Router for 2D Simulation Engine World Snapshot and Physics Controls
"""

from fastapi import APIRouter, Body
from app.services.simulator import robot_state

router = APIRouter(prefix="/api/simulation", tags=["2D Field Simulation"])

@router.get("/world")
def get_world():
    """
    Returns full snapshot of 2D field environment (plants, fruits, obstacles, robot pose, basket status).
    """
    return robot_state.get_world_snapshot()

@router.post("/start")
def start_simulation():
    """
    Start/Resume physics simulation loop.
    """
    robot_state.running = True
    return {"status": "started", "world": robot_state.get_world_snapshot()}

@router.post("/pause")
def pause_simulation():
    """
    Pause physics simulation loop.
    """
    robot_state.running = False
    return {"status": "paused", "world": robot_state.get_world_snapshot()}

@router.post("/reset")
def reset_simulation():
    """
    Reset field, robot position, fruits, obstacles, and basket back to initial state.
    """
    robot_state.reset_environment()
    return {"status": "reset", "world": robot_state.get_world_snapshot()}

@router.post("/speed")
def set_speed(speed: float = Body(..., embed=True)):
    """
    Set physics simulation speed multiplier (1.0x to 5.0x).
    """
    robot_state.speed_multiplier = max(1.0, min(5.0, speed))
    return {"speed_multiplier": robot_state.speed_multiplier}

@router.post("/step")
def step_simulation(dt: float = Body(0.1, embed=True)):
    """
    Step physics forward by dt seconds.
    """
    robot_state.step(dt)
    return robot_state.get_world_snapshot()

@router.post("/pick")
def pick_fruit():
    """
    Attempt to pick the nearest fruit within arm reach (~65 cm).
    """
    result = robot_state.pick_nearest_fruit()
    return {"result": result, "world": robot_state.get_world_snapshot()}

