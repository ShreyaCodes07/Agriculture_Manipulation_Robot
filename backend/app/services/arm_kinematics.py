"""
Agriculture Manipulation Robot - 4-DOF Manipulator Arm Kinematics & Pick-and-Place Engine
"""

import math
from typing import Dict, Any, Tuple, Optional

from app.services.simulator import robot_state
from app.models import ArmCommand, IKTargetRequest, IKTargetResponse, PickSequenceResponse

class ArmKinematicsService:
    def __init__(self):
        # Physical Link Lengths (cm)
        self.L1 = 15.0  # Base pillar height
        self.L2 = 25.0  # Upper arm length (Shoulder-to-Elbow)
        self.L3 = 20.0  # Forearm length (Elbow-to-Wrist)
        self.L4 = 10.0  # End-effector parallel gripper length

        # Trajectory Pick-and-Place State Machine
        self.sequence_state: str = "HOME"
        self.active_fruit_id: Optional[str] = None
        self.step_counter: int = 0

    def forward_kinematics(self, arm: ArmCommand) -> IKTargetRequest:
        """
        Forward Kinematics (FK): Calculates end-effector 3D Cartesian position (X, Y, Z) in cm
        from joint angles (theta_base, theta_shoulder, theta_elbow, theta_wrist).
        """
        phi_rad = math.radians(arm.theta_base)
        t2_rad = math.radians(arm.theta_shoulder)
        t3_rad = math.radians(arm.theta_elbow)
        t4_rad = math.radians(arm.theta_wrist)

        # Planar reach distance in arm vertical plane
        r = (self.L2 * math.cos(t2_rad) + 
             self.L3 * math.cos(t2_rad + t3_rad) + 
             self.L4 * math.cos(t2_rad + t3_rad + t4_rad))

        # Height above arm base
        z = (self.L1 + 
             self.L2 * math.sin(t2_rad) + 
             self.L3 * math.sin(t2_rad + t3_rad) + 
             self.L4 * math.sin(t2_rad + t3_rad + t4_rad))

        # 3D Cartesian coordinates
        x = r * math.cos(phi_rad)
        y = r * math.sin(phi_rad)

        return IKTargetRequest(
            x=round(x, 1),
            y=round(y, 1),
            z=round(z, 1),
            pitch=arm.theta_wrist
        )

    def inverse_kinematics(self, target: IKTargetRequest) -> IKTargetResponse:
        """
        Inverse Kinematics (IK): Solves joint angles (theta_1, theta_2, theta_3, theta_4)
        required to position end-effector gripper at target 3D Cartesian position (x, y, z).
        """
        x, y, z = target.x, target.y, target.z
        pitch_rad = math.radians(target.pitch)

        # 1. Base Rotation Angle (theta_1 / theta_base)
        theta_base_deg = math.degrees(math.atan2(y, x)) % 360.0
        theta_base = max(0.0, min(180.0, theta_base_deg))

        # 2. Planar target distance & effective height offset
        r_target = math.hypot(x, y) - self.L4 * math.cos(pitch_rad)
        z_target = z - self.L1 - self.L4 * math.sin(pitch_rad)
        
        D = math.hypot(r_target, z_target)

        # 3. Check workspace reach boundary
        max_reach = self.L2 + self.L3
        min_reach = abs(self.L2 - self.L3)
        
        if D > max_reach:
            # Scale target to max boundary
            r_target = r_target * (max_reach * 0.98 / D)
            z_target = z_target * (max_reach * 0.98 / D)
            D = math.hypot(r_target, z_target)
        elif D < min_reach:
            D = min_reach + 0.1

        # 4. Law of Cosines for Elbow Joint (theta_3 / theta_elbow)
        cos_t3 = (D**2 - self.L2**2 - self.L3**2) / (2.0 * self.L2 * self.L3)
        cos_t3 = max(-1.0, min(1.0, cos_t3))
        t3_rad = math.acos(cos_t3)
        theta_elbow = round(math.degrees(t3_rad), 1)

        # 5. Shoulder Joint Angle (theta_2 / theta_shoulder)
        alpha = math.atan2(z_target, r_target)
        beta = math.atan2(self.L3 * math.sin(t3_rad), self.L2 + self.L3 * math.cos(t3_rad))
        t2_rad = alpha + beta
        theta_shoulder = round(max(0.0, min(180.0, math.degrees(t2_rad))), 1)

        # 6. Wrist Pitch Angle (theta_4 / theta_wrist)
        theta_wrist = round(max(-90.0, min(90.0, target.pitch)), 1)

        sol_arm = ArmCommand(
            theta_base=round(theta_base, 1),
            theta_shoulder=round(theta_shoulder, 1),
            theta_elbow=round(theta_elbow, 1),
            theta_wrist=round(theta_wrist, 1)
        )

        fk_pos = self.forward_kinematics(sol_arm)

        return IKTargetResponse(
            success=True,
            target=target,
            arm=sol_arm,
            end_effector_pos=fk_pos,
            message=f"IK Solved: Base={sol_arm.theta_base}°, Shoulder={sol_arm.theta_shoulder}°, Elbow={sol_arm.theta_elbow}°."
        )

    def execute_pick_and_place_sequence(self, fruit_id: Optional[str] = None) -> PickSequenceResponse:
        """
        Execute 8-step Autonomous Pick-and-Place Trajectory Sequence for fruit harvesting:
        HOME -> APPROACH -> ALIGN -> GRASP -> LIFT -> DEPOSIT -> RELEASE -> RETURN_HOME.
        """
        if robot_state.estop_engaged:
            return PickSequenceResponse(
                success=False,
                sequence_step="EMERGENCY_STOP",
                arm=robot_state.arm,
                gripper_state=robot_state.gripper_state,
                harvested=False,
                basket_count=len(robot_state.basket_items),
                message="Pick-and-Place sequence blocked: EMERGENCY STOP is ENGAGED!"
            )

        # Advance step counter
        self.step_counter = (self.step_counter + 1) % 7

        if self.step_counter == 1:
            # Step 1: APPROACH TARGET
            self.sequence_state = "APPROACH"
            robot_state.arm = ArmCommand(theta_base=90.0, theta_shoulder=65.0, theta_elbow=45.0, theta_wrist=10.0)
            robot_state.gripper_state = "OPEN"
            msg = "Arm trajectory: Approaching target fruit pose."
            harvested = False

        elif self.step_counter == 2:
            # Step 2: ALIGN & GRASP
            self.sequence_state = "ALIGN"
            robot_state.arm = ArmCommand(theta_base=90.0, theta_shoulder=80.0, theta_elbow=55.0, theta_wrist=0.0)
            robot_state.gripper_state = "OPEN"
            msg = "Arm trajectory: Gripper jaws aligned around fruit body."
            harvested = False

        elif self.step_counter == 3:
            # Step 3: CLOSE GRIPPER
            self.sequence_state = "GRASP"
            robot_state.gripper_state = "CLOSE"
            msg = "End-Effector: Gripper closed with soft-touch pressure."
            harvested = False

        elif self.step_counter == 4:
            # Step 4: LIFT & DETACH
            self.sequence_state = "LIFT"
            robot_state.arm = ArmCommand(theta_base=90.0, theta_shoulder=50.0, theta_elbow=25.0, theta_wrist=-10.0)
            msg = "Arm trajectory: Lifting and detaching fruit from stem."
            harvested = False

        elif self.step_counter == 5:
            # Step 5: DEPOSIT TO REAR BASKET
            self.sequence_state = "DEPOSIT"
            robot_state.arm = ArmCommand(theta_base=170.0, theta_shoulder=60.0, theta_elbow=40.0, theta_wrist=-30.0)
            msg = "Arm trajectory: Rotated to rear onboard basket."
            harvested = False

        elif self.step_counter == 6:
            # Step 6: RELEASE FRUIT INTO BASKET
            self.sequence_state = "RELEASE"
            robot_state.gripper_state = "OPEN"
            pick_res = robot_state.pick_nearest_fruit()
            harvested = pick_res.get("success", True)
            msg = f"End-Effector: Released fruit into basket ({len(robot_state.basket_items)}/10)."

        else:
            # Step 0 / 7: RETURN HOME
            self.sequence_state = "HOME"
            robot_state.arm = ArmCommand(theta_base=90.0, theta_shoulder=45.0, theta_elbow=30.0, theta_wrist=0.0)
            robot_state.gripper_state = "OPEN"
            robot_state.mission_state = "IDLE"
            msg = "Arm trajectory: Returned to stowed HOME travel pose."
            harvested = False

        return PickSequenceResponse(
            success=True,
            sequence_step=self.sequence_state,
            arm=robot_state.arm,
            gripper_state=robot_state.gripper_state,
            harvested=harvested,
            basket_count=len(robot_state.basket_items),
            message=msg
        )

# Singleton Instance
arm_service = ArmKinematicsService()
