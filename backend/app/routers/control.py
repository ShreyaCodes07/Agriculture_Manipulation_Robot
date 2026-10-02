"""
Router for Robot Teleoperation, Arm Joint Angles, Gripper, Mode, and E-Stop
"""

from fastapi import APIRouter, HTTPException, status
from app.models import MovementCommand, ArmCommand, GripperCommand, ModeCommand, EStopCommand, RobotStatusResponse
from app.services.simulator import robot_state

router = APIRouter(prefix="/api", tags=["Control & Teleoperation"])

@router.post("/move", response_model=RobotStatusResponse)
def move_robot(cmd: MovementCommand):
    """
    Drive robot forward, backward, left, right, or stop using physics simulator kinematics.
    Blocked if Emergency Stop is engaged or obstacle distance < 30cm.
    """
    if robot_state.estop_engaged:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Movement blocked: EMERGENCY STOP is currently ENGAGED!"
        )

    # Apply drive vector to simulator
    robot_state.drive(cmd.direction, cmd.speed)
    
    # Execute an instantaneous step for teleoperation responsiveness
    robot_state.step(0.1, force=True)

    return robot_state.get_status()

@router.post("/arm", response_model=RobotStatusResponse)
def set_arm_angles(cmd: ArmCommand):
    """
    Set robotic arm joint angles (theta_base, theta_shoulder, theta_elbow, theta_wrist).
    """
    if robot_state.estop_engaged:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arm movement blocked: EMERGENCY STOP is currently ENGAGED!"
        )

    robot_state.arm = cmd
    return robot_state.get_status()

@router.post("/gripper", response_model=RobotStatusResponse)
def set_gripper(cmd: GripperCommand):
    """
    Open or close parallel gripper end-effector.
    Closing gripper will attempt to pick nearest fruit if within arm reach.
    """
    if robot_state.estop_engaged:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Gripper operation blocked: EMERGENCY STOP is currently ENGAGED!"
        )

    action = cmd.state.upper()
    if action not in ["OPEN", "CLOSE"]:
        raise HTTPException(status_code=400, detail="Invalid gripper state. Must be 'OPEN' or 'CLOSE'.")
    
    robot_state.gripper_state = action
    if action == "CLOSE":
        robot_state.pick_nearest_fruit()

    return robot_state.get_status()


@router.post("/mode", response_model=RobotStatusResponse)
def set_mode(cmd: ModeCommand):
    """
    Switch control mode between 'MANUAL' and 'AUTONOMOUS'.
    """
    mode = cmd.mode.upper()
    if mode not in ["MANUAL", "AUTONOMOUS"]:
        raise HTTPException(status_code=400, detail="Invalid mode. Must be 'MANUAL' or 'AUTONOMOUS'.")

    robot_state.control_mode = mode
    return robot_state.get_status()

@router.post("/estop", response_model=RobotStatusResponse)
def trigger_estop(cmd: EStopCommand):
    """
    Emergency Stop Override Endpoint.
    ENGAGE: Instantly halts all motion and freezes motors/arm.
    RELEASE: Restores operational readiness.
    """
    action = cmd.action.upper()
    if action == "ENGAGE":
        robot_state.estop_engaged = True
        robot_state.mission_state = "EMERGENCY_STOP"
    elif action == "RELEASE":
        robot_state.estop_engaged = False
        robot_state.mission_state = "IDLE"
    else:
        raise HTTPException(status_code=400, detail="Invalid action. Must be 'ENGAGE' or 'RELEASE'.")

    return robot_state.get_status()
