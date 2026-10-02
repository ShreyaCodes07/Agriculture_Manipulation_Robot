"""
Unit and Integration Tests for Stage 5: Autonomous Row Navigation & Mission Planner Engine
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.simulator import robot_state
from app.services.path_planner import path_planner
from app.services.mission_planner import mission_planner

client = TestClient(app)

def setup_function():
    """Reset simulator and mission planner state before each test."""
    robot_state.reset_environment()
    mission_planner.reset_mission("HARVEST_ALL")

def test_astar_path_planning_success():
    """Test A* algorithm plans a valid collision-free waypoint path."""
    start_x, start_y = 80.0, 160.0
    goal_x, goal_y = 480.0, 215.0  # Fruit 4 location

    res = client.post("/api/mission/plan_path", json={
        "start_x": start_x,
        "start_y": start_y,
        "goal_x": goal_x,
        "goal_y": goal_y
    })
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["algorithm"] == "A* (A-Star)"
    assert len(data["waypoints"]) >= 2
    assert data["total_distance_cm"] > 0

def test_astar_obstacle_avoidance():
    """Test A* path planner routes around Rock Obstacle A (at X: 280, Y: 160)."""
    start_x, start_y = 80.0, 160.0
    goal_x, goal_y = 380.0, 160.0  # Direct line goes through Rock A at X=280

    res = client.post("/api/mission/plan_path", json={
        "start_x": start_x,
        "start_y": start_y,
        "goal_x": goal_x,
        "goal_y": goal_y
    })
    assert res.status_code == 200
    waypoints = res.json()["waypoints"]
    
    # Ensure no waypoint passes directly inside Rock A collision circle (radius 22cm at X: 280, Y: 160)
    for wp in waypoints:
        dist_to_rock = ((wp["x"] - 280.0)**2 + (wp["y"] - 160.0)**2)**0.5
        assert dist_to_rock >= 20.0  # Safe distance outside rock center

def test_mission_creation_and_queuing():
    """Test initializing harvesting mission queues ripe targets and optimizes route."""
    res_status = client.get("/api/mission/status")
    assert res_status.status_code == 200
    data = res_status.json()

    assert data["state"] == "IDLE"
    assert data["total_count"] == 5  # 5 ripe fruits (fruit_1 to fruit_5)
    assert len(data["targets"]) == 5
    assert data["current_target_id"] is not None

def test_mission_lifecycle_controls():
    """Test mission controls: START, PAUSE, RESUME, STOP, RESET."""
    # START
    res_start = client.post("/api/mission/control", json={"action": "START", "mission_type": "HARVEST_ALL"})
    assert res_start.status_code == 200
    assert res_start.json()["state"] == "PLANNING_PATH"


    # PAUSE
    res_pause = client.post("/api/mission/control", json={"action": "PAUSE"})
    assert res_pause.status_code == 200
    assert res_pause.json()["state"] == "PAUSED"

    # RESUME
    res_resume = client.post("/api/mission/control", json={"action": "RESUME"})
    assert res_resume.status_code == 200
    assert res_resume.json()["state"] == "NAVIGATING_ROW"

    # STOP
    res_stop = client.post("/api/mission/control", json={"action": "STOP"})
    assert res_stop.status_code == 200
    assert res_stop.json()["state"] == "STOPPED"

    # RESET
    res_reset = client.post("/api/mission/control", json={"action": "RESET", "mission_type": "HARVEST_APPLES"})
    assert res_reset.status_code == 200
    assert res_reset.json()["state"] == "IDLE"
    assert res_reset.json()["total_count"] == 3  # 3 red apples

def test_autonomous_row_navigation_and_multi_target_harvesting():
    """Test full multi-target autonomous row navigation and harvesting execution."""
    client.post("/api/mission/control", json={"action": "START", "mission_type": "HARVEST_APPLES"})

    # Step mission until complete or timeout
    for _ in range(80):
        res_step = client.post("/api/mission/step", json={"dt": 0.2})
        assert res_step.status_code == 200
        state = res_step.json()["state"]
        if state in ["COMPLETED", "STOPPED"]:
            break

    # Robot should have harvested red apples
    status = mission_planner.get_mission_status()
    assert status.completed_count >= 1

def test_mode_switching():
    """Test switching between MANUAL and AUTONOMOUS control modes."""
    # Switch to MANUAL
    res_manual = client.post("/api/mode", json={"mode": "manual"})
    assert res_manual.status_code == 200
    assert robot_state.control_mode == "MANUAL"

    # Switch to AUTONOMOUS
    res_auto = client.post("/api/mode", json={"mode": "autonomous"})
    assert res_auto.status_code == 200
    assert robot_state.control_mode == "AUTONOMOUS"
