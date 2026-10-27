"""
Unit and Integration Tests for Stage 3: Simulation Engine & 2D Field Canvas
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.simulator import robot_state

client = TestClient(app)

def setup_function():
    """Reset simulator environment before each test."""
    robot_state.reset_environment()

def test_simulation_world_snapshot():
    """Verify that /api/simulation/world returns complete environment snapshot."""
    response = client.get("/api/simulation/world")
    assert response.status_code == 200
    data = response.json()
    assert "field" in data
    assert "robot" in data
    assert "fruits" in data
    assert "obstacles" in data
    assert "basket" in data
    assert "sim_status" in data
    assert len(data["field"]["rows"]) == 3
    assert len(data["fruits"]) == 6
    assert len(data["obstacles"]) == 2

def test_root_serves_spa_frontend():
    """Verify that GET / returns the HTML Single Page Application."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "Agriculture Manipulation Robot" in response.text

def test_api_info_endpoint():
    """Verify that GET /api returns JSON project metadata."""
    response = client.get("/api")
    assert response.status_code == 200
    data = response.json()
    assert "project" in data
    assert "version" in data
    assert data["status"] == "ONLINE"

def test_simulation_start_pause_reset():
    """Test start, pause, and reset simulation endpoints."""
    # Start
    res_start = client.post("/api/simulation/start")
    assert res_start.status_code == 200
    assert robot_state.running is True

    # Pause
    res_pause = client.post("/api/simulation/pause")
    assert res_pause.status_code == 200
    assert robot_state.running is False

    # Reset
    res_reset = client.post("/api/simulation/reset")
    assert res_reset.status_code == 200
    assert robot_state.pose.x == 80.0
    assert robot_state.pose.y == 160.0

def test_robot_teleoperation_kinematics():
    """Test manual teleoperation movement and position update."""
    initial_x = robot_state.pose.x
    initial_y = robot_state.pose.y

    # Drive forward
    res_move = client.post("/api/move", json={"direction": "forward", "speed": 1.0})
    assert res_move.status_code == 200
    # Pose heading 0.0 deg -> moves +X
    assert robot_state.pose.x > initial_x
    assert robot_state.pose.y == initial_y

def test_fruit_picking_mechanic():
    """Test approaching a fruit and executing fruit harvest action."""
    # Position robot near fruit_1 (Ripe Red Apple at X: 180, Y: 95)
    robot_state.pose.x = 175.0
    robot_state.pose.y = 95.0

    res_pick = client.post("/api/simulation/pick")
    assert res_pick.status_code == 200
    data = res_pick.json()
    assert data["result"]["success"] is True
    assert "Ripe Red Apple" in data["result"]["message"]
    assert len(robot_state.basket_items) == 1

def test_unripe_fruit_picking_rejection():
    """Test that vision color filter rejects harvesting unripe fruit."""
    # Position robot near fruit_6 (Unripe Green Fruit at X: 560, Y: 335)
    robot_state.pose.x = 555.0
    robot_state.pose.y = 335.0

    res_pick = client.post("/api/simulation/pick")
    assert res_pick.status_code == 200
    data = res_pick.json()
    assert data["result"]["success"] is False
    assert "unripe" in data["result"]["message"].lower()

def test_estop_override():
    """Test Emergency Stop engagement blocks movement and arm commands."""
    # Engage E-Stop
    res_estop = client.post("/api/estop", json={"action": "ENGAGE"})
    assert res_estop.status_code == 200
    assert robot_state.estop_engaged is True

    # Attempt movement while E-Stop engaged -> should return HTTP 400
    res_move = client.post("/api/move", json={"direction": "forward", "speed": 1.0})
    assert res_move.status_code == 400

    # Release E-Stop
    res_release = client.post("/api/estop", json={"action": "RELEASE"})
    assert res_release.status_code == 200
    assert robot_state.estop_engaged is False

def test_obstacle_hazard_braking():
    """Test ultrasonic hazard sensor auto-braking when approaching obstacle."""
    # Place robot right in front of Rock Obstacle A (at X: 280, Y: 160) facing right (heading 0)
    robot_state.pose.x = 245.0
    robot_state.pose.y = 160.0
    robot_state.pose.heading = 0.0
    robot_state.update_sensors()

    # Distance to rock radius (22cm) from chassis edge should be < 30cm
    assert robot_state.sensors.obstacle_warning is True
    assert robot_state.sensors.distance_cm < 30.0

    # Driving forward should halt linear velocity
    client.post("/api/move", json={"direction": "forward", "speed": 1.0})
    assert robot_state.linear_velocity == 0.0
