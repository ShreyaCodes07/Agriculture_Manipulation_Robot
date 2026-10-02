"""
Pydantic Schemas & Data Transfer Objects (DTOs)
"""

from typing import List, Optional
from pydantic import BaseModel, Field

# --- Movement & Teleoperation Schemas ---
class MovementCommand(BaseModel):
    direction: str = Field(..., description="Movement direction: 'forward', 'backward', 'left', 'right', or 'stop'")
    speed: float = Field(default=1.0, ge=0.0, le=2.0, description="Linear velocity magnitude (m/s)")

# --- Arm Kinematics Schemas ---
class ArmCommand(BaseModel):
    theta_base: float = Field(default=90.0, ge=0.0, le=180.0, description="Base rotation angle (degrees)")
    theta_shoulder: float = Field(default=45.0, ge=0.0, le=180.0, description="Shoulder joint angle (degrees)")
    theta_elbow: float = Field(default=30.0, ge=0.0, le=180.0, description="Elbow joint angle (degrees)")
    theta_wrist: float = Field(default=0.0, ge=-90.0, le=90.0, description="Wrist pitch angle (degrees)")

class IKTargetRequest(BaseModel):
    x: float = Field(..., description="Target 3D X coordinate relative to arm base (cm)")
    y: float = Field(..., description="Target 3D Y coordinate relative to arm base (cm)")
    z: float = Field(default=10.0, description="Target 3D Z height coordinate relative to arm base (cm)")
    pitch: float = Field(default=0.0, description="Desired wrist pitch angle in degrees")

class IKTargetResponse(BaseModel):
    success: bool
    target: IKTargetRequest
    arm: ArmCommand
    end_effector_pos: IKTargetRequest
    message: str

class PickSequenceRequest(BaseModel):
    fruit_id: Optional[str] = Field(default=None, description="ID of target fruit to pick")
    speed: float = Field(default=1.0, ge=0.5, le=3.0)

class PickSequenceResponse(BaseModel):
    success: bool
    sequence_step: str = Field(..., description="HOME, APPROACH, ALIGN, GRASP, LIFT, DEPOSIT, COMPLETED")
    arm: ArmCommand
    gripper_state: str
    harvested: bool
    basket_count: int
    message: str


# --- End-Effector Gripper Schema ---
class GripperCommand(BaseModel):
    state: str = Field(..., description="Gripper action: 'OPEN' or 'CLOSE'")

# --- System Mode Toggle Schema ---
class ModeCommand(BaseModel):
    mode: str = Field(..., description="Execution mode: 'manual' or 'autonomous'")

# --- Emergency Stop Schema ---
class EStopCommand(BaseModel):
    action: str = Field(..., description="E-Stop action: 'ENGAGE' or 'RELEASE'")

# --- Sensor Readout Schemas ---
class SensorData(BaseModel):
    distance_cm: float = Field(default=85.0, description="Ultrasonic distance sensor reading in cm")
    soil_moisture_percent: float = Field(default=42.0, description="Analog soil moisture percentage")
    obstacle_warning: bool = Field(default=False, description="Collision hazard flag")

# --- Robot Spatial Pose Schema ---
class RobotPose(BaseModel):
    x: float = Field(default=120.0, description="Field X coordinate in cm")
    y: float = Field(default=250.0, description="Field Y coordinate in cm")
    heading: float = Field(default=0.0, description="Robot heading orientation in degrees")

# --- Full Robot Telemetry Status Schema ---
class RobotStatusResponse(BaseModel):
    operation_mode: str = Field(..., description="Current system mode: 'SIMULATION' or 'HARDWARE'")
    control_mode: str = Field(..., description="Control mode: 'MANUAL' or 'AUTONOMOUS'")
    estop_engaged: bool = Field(..., description="Emergency stop status")
    pose: RobotPose
    arm: ArmCommand
    gripper_state: str
    sensors: SensorData
    mission_state: str = Field(default="IDLE", description="Autonomous state machine phase")

# --- Vision Detection Schemas ---
class DetectedFruitObject(BaseModel):
    fruit_id: str = Field(..., description="Unique ID of the detected fruit")
    label: str = Field(..., description="Classification label (e.g., Ripe Red Apple)")
    confidence: float = Field(..., description="Detection confidence score (0.0 - 1.0)")
    bbox: List[int] = Field(..., description="Bounding box [x, y, width, height] in image pixels")
    center_img: List[int] = Field(..., description="Image centroid [cx, cy]")
    field_x: float = Field(..., description="Mapped field X coordinate in cm")
    field_y: float = Field(..., description="Mapped field Y coordinate in cm")
    is_target: bool = Field(default=False, description="Whether fruit is active navigation target")
    is_ripe: bool = Field(default=True, description="Whether fruit is ripe for picking")
    distance_cm: float = Field(default=0.0, description="Estimated distance from robot camera")

class VisionDetectionResponse(BaseModel):
    success: bool
    active: bool
    detected_count: int
    target_fruit_id: Optional[str] = None
    camera_frame_b64: str = Field(default="", description="Base64 encoded JPEG annotated camera frame")
    objects: List[DetectedFruitObject]
    message: str = Field(default="Vision pipeline active")

class TargetSelectCommand(BaseModel):
    fruit_id: str = Field(..., description="ID of fruit target to lock onto")

class HSVThresholdCommand(BaseModel):
    h_min: int = Field(default=0, ge=0, le=180)
    s_min: int = Field(default=100, ge=0, le=255)
    v_min: int = Field(default=100, ge=0, le=255)
    h_max: int = Field(default=10, ge=0, le=180)
    s_max: int = Field(default=255, ge=0, le=255)
    v_max: int = Field(default=255, ge=0, le=255)

# --- Path Planning & Mission Planner Schemas ---
class WaypointModel(BaseModel):
    x: float = Field(..., description="Waypoint field X coordinate in cm")
    y: float = Field(..., description="Waypoint field Y coordinate in cm")

class PathPlanRequest(BaseModel):
    start_x: float = Field(..., description="Start X coordinate in cm")
    start_y: float = Field(..., description="Start Y coordinate in cm")
    goal_x: float = Field(..., description="Goal X coordinate in cm")
    goal_y: float = Field(..., description="Goal Y coordinate in cm")

class PathPlanResponse(BaseModel):
    success: bool
    algorithm: str = Field(default="A* (A-Star)")
    start: WaypointModel
    goal: WaypointModel
    waypoints: List[WaypointModel]
    total_distance_cm: float
    message: str

class MissionTargetStatus(BaseModel):
    fruit_id: str
    label: str
    status: str = Field(..., description="PENDING, ACTIVE, HARVESTED, SKIPPED, FAILED")
    field_x: float
    field_y: float

class MissionStatusResponse(BaseModel):
    mission_id: str
    name: str
    state: str = Field(..., description="IDLE, PLANNING_PATH, NAVIGATING_ROW, HARVESTING, PAUSED, COMPLETED, STOPPED")
    progress_percent: float
    current_target_id: Optional[str] = None
    current_waypoint_index: int = 0
    targets: List[MissionTargetStatus]
    planned_path: List[WaypointModel]
    completed_count: int
    total_count: int
    message: str

class MissionControlCommand(BaseModel):
    action: str = Field(..., description="START, PAUSE, RESUME, STOP, RESET")
    mission_type: Optional[str] = Field(default="HARVEST_ALL", description="HARVEST_ALL, HARVEST_APPLES, HARVEST_LEMONS, ROW_SWEEP")



# --- Mission Log & Test Result Schemas ---
class LogEntry(BaseModel):
    id: Optional[int] = None
    timestamp: str
    level: str
    message: str

class TestResultModel(BaseModel):
    test_id: str
    scenario: str
    expected: str
    actual: str
    mode: str
    status: str
