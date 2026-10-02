"""
Router for 4-DOF Robotic Arm Manipulator, Inverse Kinematics, and Pick-and-Place Trajectories
"""

from fastapi import APIRouter, HTTPException, status
from app.models import ArmCommand, GripperCommand, IKTargetRequest, IKTargetResponse, PickSequenceRequest, PickSequenceResponse
from app.services.simulator import robot_state
from app.services.arm_kinematics import arm_service

router = APIRouter(prefix="/api/arm", tags=["4-DOF Manipulator Arm"])

@router.get("/status")
def get_arm_status():
    """
    Returns full status of 4-DOF arm joint angles, end-effector 3D Cartesian position, and gripper state.
    """
    fk_pos = arm_service.forward_kinematics(robot_state.arm)
    return {
        "arm": robot_state.arm,
        "gripper_state": robot_state.gripper_state,
        "end_effector_pos": fk_pos,
        "sequence_state": arm_service.sequence_state
    }

@router.post("/joints")
def set_arm_joints(cmd: ArmCommand):
    """
    Set 4-DOF robotic arm joint angles directly (theta_base, theta_shoulder, theta_elbow, theta_wrist).
    """
    if robot_state.estop_engaged:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arm movement blocked: EMERGENCY STOP is ENGAGED!"
        )
    # Clamp joint angles to physical mechanical limits
    cmd.theta_base = max(0.0, min(180.0, cmd.theta_base))
    cmd.theta_shoulder = max(0.0, min(135.0, cmd.theta_shoulder))
    cmd.theta_elbow = max(0.0, min(135.0, cmd.theta_elbow))
    cmd.theta_wrist = max(-90.0, min(90.0, cmd.theta_wrist))

    robot_state.arm = cmd
    fk_pos = arm_service.forward_kinematics(cmd)
    return {
        "status": "success",
        "arm": robot_state.arm,
        "end_effector_pos": fk_pos
    }

@router.post("/ik", response_model=IKTargetResponse)
def solve_inverse_kinematics(req: IKTargetRequest):
    """
    Solve Inverse Kinematics (IK) for 3D target position (X, Y, Z) and position arm joints.
    """
    if robot_state.estop_engaged:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="IK movement blocked: EMERGENCY STOP is ENGAGED!"
        )
    ik_res = arm_service.inverse_kinematics(req)
    if ik_res.success:
        robot_state.arm = ik_res.arm
    return ik_res

@router.post("/pick_sequence", response_model=PickSequenceResponse)
def run_pick_sequence(req: PickSequenceRequest = PickSequenceRequest()):
    """
    Step through 8-stage Autonomous Pick-and-Place Trajectory Sequence for fruit harvesting.
    """
    return arm_service.execute_pick_and_place_sequence(req.fruit_id)

@router.post("/gripper")
def set_gripper_state(cmd: GripperCommand):
    """
    Open or close end-effector parallel gripper jaws.
    """
    if robot_state.estop_engaged:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Gripper blocked: EMERGENCY STOP is ENGAGED!"
        )
    robot_state.gripper_state = cmd.state.upper()
    if cmd.state.upper() == "CLOSE":
        robot_state.pick_nearest_fruit()
    return {
        "status": "success",
        "gripper_state": robot_state.gripper_state,
        "basket_count": len(robot_state.basket_items)
    }
