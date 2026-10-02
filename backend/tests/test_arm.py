"""
Unit and Integration Tests for Stage 6: 4-DOF Robotic Arm Manipulation & Autonomous Fruit Picking
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.simulator import robot_state
from app.services.arm_kinematics import arm_service
from app.models import ArmCommand

client = TestClient(app)

def setup_function():
    """Reset robot state and arm parameters before each test."""
    robot_state.reset_environment()
    robot_state.arm = ArmCommand(
        theta_base=90.0,
        theta_shoulder=45.0,
        theta_elbow=30.0,
        theta_wrist=0.0
    )
    robot_state.gripper_state = "OPEN"
    arm_service.step_counter = 0
    arm_service.sequence_state = "HOME"

def test_get_arm_status():
    """Test retrieving initial arm status and end-effector 3D position."""
    res = client.get("/api/arm/status")
    assert res.status_code == 200
    data = res.json()
    assert "arm" in data
    assert data["arm"]["theta_base"] == 90.0
    assert data["arm"]["theta_shoulder"] == 45.0
    assert data["arm"]["theta_elbow"] == 30.0
    assert data["arm"]["theta_wrist"] == 0.0
    assert data["gripper_state"] == "OPEN"
    assert "end_effector_pos" in data
    assert "x" in data["end_effector_pos"]
    assert "y" in data["end_effector_pos"]
    assert "z" in data["end_effector_pos"]

def test_set_arm_joints_with_clamping():
    """Test setting arm joint angles via API with range boundary clamping."""
    res = client.post("/api/arm/joints", json={
        "theta_base": 120.0,
        "theta_shoulder": 150.0,  # Max allowed is 135.0 -> should clamp to 135
        "theta_elbow": 60.0,
        "theta_wrist": -45.0
    })
    assert res.status_code == 200
    data = res.json()
    assert data["arm"]["theta_base"] == 120.0
    assert data["arm"]["theta_shoulder"] == 135.0  # Clamped
    assert data["arm"]["theta_elbow"] == 60.0
    assert data["arm"]["theta_wrist"] == -45.0

def test_forward_kinematics_computation():
    """Test direct Forward Kinematics position math calculation."""
    arm_cmd = ArmCommand(theta_base=90.0, theta_shoulder=0.0, theta_elbow=0.0, theta_wrist=0.0)
    pos = arm_service.forward_kinematics(arm_cmd)
    # At base angle 90° (forward direction) and 0° joints:
    # X should be L2 + L3 + L4 = 25 + 20 + 10 = 55 cm
    # Y should be ~0 cm
    # Z should be L1 = 15 cm
    assert abs(pos.x - 0.0) < 1.0  # x = r * cos(90°) = 0
    assert abs(pos.y - 55.0) < 1.0 # y = r * sin(90°) = 55
    assert abs(pos.z - 15.0) < 1.0

def test_inverse_kinematics_solver_success():
    """Test Inverse Kinematics calculation for reachable target."""
    res_reach = client.post("/api/arm/ik", json={"x": 25.0, "y": 0.0, "z": 15.0, "pitch": 0.0})
    assert res_reach.status_code == 200
    data_reach = res_reach.json()
    assert data_reach["success"] is True
    assert "arm" in data_reach
    assert data_reach["arm"]["theta_base"] == 0.0

def test_gripper_open_close_control():
    """Test parallel end-effector gripper opening and closing commands."""
    # Close Gripper
    res_close = client.post("/api/arm/gripper", json={"state": "CLOSE"})
    assert res_close.status_code == 200
    assert res_close.json()["gripper_state"] == "CLOSE"
    assert robot_state.gripper_state == "CLOSE"

    # Open Gripper
    res_open = client.post("/api/arm/gripper", json={"state": "OPEN"})
    assert res_open.status_code == 200
    assert res_open.json()["gripper_state"] == "OPEN"
    assert robot_state.gripper_state == "OPEN"

def test_8_step_pick_and_place_sequence_execution():
    """Test executing the 8-step autonomous pick-and-place trajectory state machine."""
    expected_states = [
        "APPROACH",
        "ALIGN",
        "GRASP",
        "LIFT",
        "DEPOSIT",
        "RELEASE",
        "HOME"
    ]

    for expected_state in expected_states:
        res = client.post("/api/arm/pick_sequence")
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["sequence_step"] == expected_state

    # Verify gripper is open after completing trajectory back to HOME
    assert robot_state.gripper_state == "OPEN"
