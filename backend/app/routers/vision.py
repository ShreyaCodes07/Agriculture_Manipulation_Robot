"""
Router for Computer Vision Fruit Target Detection & Autonomous Navigation
"""

from fastapi import APIRouter
from app.models import VisionDetectionResponse, TargetSelectCommand, HSVThresholdCommand
from app.services.vision import vision_service

router = APIRouter(prefix="/api/vision", tags=["Computer Vision & Fruit Detection"])

@router.get("/detect", response_model=VisionDetectionResponse)
def get_vision_detections():
    """
    Execute OpenCV fruit detection pipeline and return detected objects, bounding boxes, 
    mapped coordinates, and annotated JPEG Base64 camera frame.
    """
    return vision_service.run_detection_pipeline()

@router.post("/start")
def start_detection():
    """
    Start/Resume computer vision pipeline.
    """
    vision_service.active = True
    return {"status": "started", "active": True}

@router.post("/stop")
def stop_detection():
    """
    Pause computer vision pipeline.
    """
    vision_service.active = False
    return {"status": "stopped", "active": False}

@router.post("/select_target")
def select_target(cmd: TargetSelectCommand):
    """
    Lock computer vision pipeline target onto a specific fruit ID.
    """
    return vision_service.set_target_fruit(cmd.fruit_id)

@router.post("/navigate")
def navigate_target():
    """
    Execute autonomous closed-loop navigation step toward selected target fruit.
    Auto-harvests fruit upon reaching arm reach distance.
    """
    return vision_service.navigate_towards_target()

@router.post("/hsv")
def set_hsv_thresholds(cmd: HSVThresholdCommand):
    """
    Update HSV color segmentation thresholds dynamically.
    """
    vision_service.update_hsv_thresholds(cmd)
    return {"status": "hsv_updated", "cmd": cmd}
