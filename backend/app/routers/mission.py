"""
Router for Autonomous Row Navigation, A* Path Planning, and Mission Control
"""

from fastapi import APIRouter, Body
from app.models import MissionStatusResponse, MissionControlCommand, PathPlanRequest, PathPlanResponse
from app.services.mission_planner import mission_planner
from app.services.path_planner import path_planner

router = APIRouter(prefix="/api/mission", tags=["Mission Planner & Row Navigation"])

@router.get("/status", response_model=MissionStatusResponse)
def get_mission_status():
    """
    Returns full snapshot of active harvesting mission, target queue, and planned A* path.
    """
    return mission_planner.get_mission_status()

@router.post("/control", response_model=MissionStatusResponse)
def control_mission(cmd: MissionControlCommand):
    """
    Execute user mission control actions (START, PAUSE, RESUME, STOP, RESET).
    """
    return mission_planner.handle_command(cmd)

@router.post("/plan_path", response_model=PathPlanResponse)
def plan_custom_path(req: PathPlanRequest):
    """
    Plan collision-free A* (A-Star) path between custom start and goal coordinates.
    """
    return path_planner.plan_path(req.start_x, req.start_y, req.goal_x, req.goal_y)

@router.post("/step", response_model=MissionStatusResponse)
def step_mission(dt: float = Body(0.1, embed=True)):
    """
    Step autonomous mission execution state machine forward by dt seconds.
    """
    return mission_planner.step_mission(dt)
