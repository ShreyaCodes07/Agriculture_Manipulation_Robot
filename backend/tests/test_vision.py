"""
Unit and Integration Tests for Stage 4: Computer Vision Pipeline & Target Detection Engine
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.simulator import robot_state
from app.services.vision import vision_service

client = TestClient(app)

def setup_function():
    """Reset environment and vision service state before each test."""
    robot_state.reset_environment()
    vision_service.active = True
    vision_service.target_fruit_id = "fruit_1"

def test_vision_detection_endpoint():
    """Test /api/vision/detect endpoint returns bounding boxes and annotated camera frame."""
    response = client.get("/api/vision/detect")
    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert data["active"] is True
    assert "camera_frame_b64" in data
    assert data["camera_frame_b64"].startswith("data:image/jpeg;base64,")
    assert "objects" in data
    assert len(data["objects"]) > 0

    # Inspect first detected object structure
    obj = data["objects"][0]
    assert "fruit_id" in obj
    assert "label" in obj
    assert "confidence" in obj
    assert len(obj["bbox"]) == 4  # [x, y, w, h]
    assert "field_x" in obj
    assert "field_y" in obj
    assert "distance_cm" in obj

def test_target_selection():
    """Test locking vision target onto specific fruit ID."""
    res_select = client.post("/api/vision/select_target", json={"fruit_id": "fruit_3"})
    assert res_select.status_code == 200
    assert vision_service.target_fruit_id == "fruit_3"

    res_detect = client.get("/api/vision/detect")
    assert res_detect.json()["target_fruit_id"] == "fruit_3"

def test_vision_start_stop():
    """Test pausing and resuming the computer vision pipeline."""
    # Stop
    res_stop = client.post("/api/vision/stop")
    assert res_stop.status_code == 200
    assert vision_service.active is False

    res_detect_paused = client.get("/api/vision/detect")
    assert res_detect_paused.json()["active"] is False

    # Start
    res_start = client.post("/api/vision/start")
    assert res_start.status_code == 200
    assert vision_service.active is True

def test_coordinate_mapping():
    """Test 2D image pixel coordinate to 2D field world coordinate mapping formula."""
    mapping = vision_service.map_image_to_world_coords(
        img_x=320,  # Center pixel
        bbox_w=40,
        robot_pose=robot_state.pose
    )
    assert mapping["field_x"] > robot_state.pose.x
    assert mapping["distance_cm"] > 0

def test_autonomous_target_navigation():
    """Test target navigation steering, forward drive, and automatic fruit picking."""
    # Target 1 (Ripe Red Apple at X: 180, Y: 95)
    vision_service.set_target_fruit("fruit_1")

    # Perform navigation steps
    for _ in range(30):
        res_nav = client.post("/api/vision/navigate")
        assert res_nav.status_code == 200
        status = res_nav.json()["status"]
        if status == "harvested":
            break

    # Robot should have successfully harvested Target 1
    assert "fruit_1" not in [f.id for f in robot_state.fruits if not f.picked]
    assert len(robot_state.basket_items) == 1

