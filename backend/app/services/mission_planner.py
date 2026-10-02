"""
Agriculture Manipulation Robot - Mission Planner & Autonomous Row Navigation State Machine
"""

import math
from typing import List, Dict, Any, Optional

from app.services.simulator import robot_state
from app.services.path_planner import path_planner, WaypointModel
from app.services.vision import vision_service
from app.models import MissionStatusResponse, MissionTargetStatus, MissionControlCommand

class MissionPlannerService:
    def __init__(self):
        self.mission_id: str = "MISSION_001"
        self.mission_name: str = "Full Field Harvesting Mission"
        self.state: str = "IDLE"  # IDLE, PLANNING_PATH, NAVIGATING_ROW, APPROACHING_TARGET, HARVESTING, PAUSED, STOPPED, COMPLETED
        self.mission_type: str = "HARVEST_ALL"
        
        self.targets: List[MissionTargetStatus] = []
        self.current_target_index: int = 0
        self.current_target_id: Optional[str] = None
        
        self.planned_path: List[WaypointModel] = []
        self.current_waypoint_index: int = 0
        
        self.completed_count: int = 0
        self.total_count: int = 0
        self.status_message: str = "Mission Planner initialized in IDLE state."

        # Pre-populate default mission targets
        self.reset_mission()

    def reset_mission(self, mission_type: str = "HARVEST_ALL") -> MissionStatusResponse:
        """Reset mission planner state, queue targets, and clear active paths."""
        self.mission_type = mission_type
        self.state = "IDLE"
        self.planned_path = []
        self.current_waypoint_index = 0
        self.completed_count = 0
        self.current_target_index = 0
        self.current_target_id = None
        
        robot_state.control_mode = "AUTONOMOUS"
        robot_state.mission_state = "IDLE"

        # Build target queue based on mission type
        self.targets = []
        for fruit in robot_state.fruits:
            is_ripe = "Ripe" in fruit.label or "Yellow" in fruit.label or fruit.color != "#4caf50"
            
            if mission_type == "HARVEST_ALL" and is_ripe:
                self.targets.append(MissionTargetStatus(
                    fruit_id=fruit.id, label=fruit.label, status="PENDING", field_x=fruit.x, field_y=fruit.y
                ))
            elif mission_type == "HARVEST_APPLES" and "Apple" in fruit.label and is_ripe:
                self.targets.append(MissionTargetStatus(
                    fruit_id=fruit.id, label=fruit.label, status="PENDING", field_x=fruit.x, field_y=fruit.y
                ))
            elif mission_type == "HARVEST_LEMONS" and "Lemon" in fruit.label:
                self.targets.append(MissionTargetStatus(
                    fruit_id=fruit.id, label=fruit.label, status="PENDING", field_x=fruit.x, field_y=fruit.y
                ))

        # Optimize visiting order (Greedy Nearest Neighbor TSP)
        self.optimize_target_visiting_order()

        self.total_count = len(self.targets)
        if self.targets:
            self.current_target_id = self.targets[0].fruit_id
            self.targets[0].status = "PENDING"

        self.status_message = f"Mission reset for '{mission_type}'. Queued {self.total_count} target fruits."
        return self.get_mission_status()

    def optimize_target_visiting_order(self):
        """Greedy Nearest-Neighbor TSP optimization to minimize total driving distance across plant rows."""
        if not self.targets:
            return

        unvisited = list(self.targets)
        ordered: List[MissionTargetStatus] = []
        cur_x, cur_y = robot_state.pose.x, robot_state.pose.y

        while unvisited:
            # Find closest unvisited target
            best_target = min(unvisited, key=lambda t: math.hypot(t.field_x - cur_x, t.field_y - cur_y))
            ordered.append(best_target)
            unvisited.remove(best_target)
            cur_x, cur_y = best_target.field_x, best_target.field_y

        self.targets = ordered

    def handle_command(self, cmd: MissionControlCommand) -> MissionStatusResponse:
        """Handle user mission control commands (START, PAUSE, RESUME, STOP, RESET)."""
        action = cmd.action.upper()

        if action == "RESET":
            return self.reset_mission(cmd.mission_type or "HARVEST_ALL")
        elif action == "START":
            if self.state in ["COMPLETED", "STOPPED"] or not self.targets:
                self.reset_mission(cmd.mission_type or "HARVEST_ALL")
            self.state = "PLANNING_PATH"
            robot_state.running = True
            robot_state.control_mode = "AUTONOMOUS"
            self.status_message = "Mission started. Planning initial A* row navigation path."
        elif action == "PAUSE":
            self.state = "PAUSED"
            robot_state.running = False
            robot_state.drive("stop")
            self.status_message = "Mission PAUSED by user."
        elif action == "RESUME":
            self.state = "NAVIGATING_ROW"
            robot_state.running = True
            robot_state.control_mode = "AUTONOMOUS"
            self.status_message = "Mission RESUMED."
        elif action == "STOP":
            self.state = "STOPPED"
            robot_state.running = False
            robot_state.drive("stop")
            self.status_message = "Mission STOPPED by user."

        return self.get_mission_status()

    def step_mission(self, dt: float = 0.1) -> MissionStatusResponse:
        """
        Execute 1 step of Autonomous Mission Control State Machine.
        Handles row navigation, A* waypoint tracking, obstacle avoidance, and fruit harvesting.
        """
        if robot_state.estop_engaged:
            self.state = "EMERGENCY_STOP"
            self.status_message = "🚨 MISSION INTERRUPTED: Emergency Stop is ENGAGED!"
            return self.get_mission_status()

        if self.state in ["IDLE", "PAUSED", "STOPPED", "COMPLETED"]:
            return self.get_mission_status()

        # Check if all targets are completed
        if self.current_target_index >= len(self.targets):
            self.state = "COMPLETED"
            robot_state.running = False
            robot_state.drive("stop")
            robot_state.mission_state = "MISSION_COMPLETED"
            self.status_message = f"🎉 MISSION COMPLETED! Successfully harvested {self.completed_count}/{self.total_count} fruits."
            return self.get_mission_status()

        active_target = self.targets[self.current_target_index]
        self.current_target_id = active_target.fruit_id
        active_target.status = "ACTIVE"
        vision_service.set_target_fruit(active_target.fruit_id)

        # 1. State: PLANNING_PATH (Generate A* path to active target)
        if self.state == "PLANNING_PATH" or not self.planned_path:
            cur_pose = robot_state.pose
            path_res = path_planner.plan_path(
                cur_pose.x, cur_pose.y, active_target.field_x, active_target.field_y
            )
            self.planned_path = path_res.waypoints
            self.current_waypoint_index = 0
            self.state = "NAVIGATING_ROW"
            self.status_message = f"A* Path generated ({len(self.planned_path)} waypoints) to target '{active_target.fruit_id}'."

        # 2. State: NAVIGATING_ROW (Waypoint Following Kinematics)
        if self.state == "NAVIGATING_ROW":
            if self.current_waypoint_index < len(self.planned_path):
                wp = self.planned_path[self.current_waypoint_index]
                cur_pose = robot_state.pose

                dx = wp.x - cur_pose.x
                dy = wp.y - cur_pose.y
                dist_to_wp = math.hypot(dx, dy)

                if dist_to_wp < 25.0:  # Reached waypoint cell
                    self.current_waypoint_index += 1
                    if self.current_waypoint_index >= len(self.planned_path):
                        self.state = "APPROACHING_TARGET"
                else:
                    # Steer & Drive toward waypoint
                    target_angle_deg = math.degrees(math.atan2(dy, dx)) % 360.0
                    angle_err = (target_angle_deg - cur_pose.heading + 180) % 360 - 180

                    if abs(angle_err) > 8.0:
                        turn_rate = max(-60.0, min(60.0, angle_err * 3.0))
                        robot_state.angular_velocity = turn_rate
                        robot_state.linear_velocity = 0.0
                    else:
                        robot_state.linear_velocity = max(25.0, min(50.0, dist_to_wp * 0.8))
                        robot_state.angular_velocity = 0.0

                    robot_state.step(dt, force=True)
                    robot_state.mission_state = f"NAVIGATING_ROW (Wp {self.current_waypoint_index+1}/{len(self.planned_path)})"

        # 3. State: APPROACHING_TARGET & HARVESTING (Vision Alignment & Arm Pick)
        if self.state == "APPROACHING_TARGET":
            nav_res = vision_service.navigate_towards_target()
            if nav_res["status"] == "harvested":
                active_target.status = "HARVESTED"
                self.completed_count += 1
                self.current_target_index += 1
                self.planned_path = []
                self.state = "PLANNING_PATH"
                self.status_message = f"Harvested target '{active_target.fruit_id}'. Moving to next target..."
            elif nav_res["status"] == "failed":
                active_target.status = "SKIPPED"
                self.current_target_index += 1
                self.planned_path = []
                self.state = "PLANNING_PATH"

        return self.get_mission_status()

    def get_mission_status(self) -> MissionStatusResponse:
        """Return full current mission status payload."""
        progress = (self.completed_count / self.total_count * 100.0) if self.total_count > 0 else 0.0
        return MissionStatusResponse(
            mission_id=self.mission_id,
            name=self.mission_name,
            state=self.state,
            progress_percent=round(progress, 1),
            current_target_id=self.current_target_id,
            current_waypoint_index=self.current_waypoint_index,
            targets=self.targets,
            planned_path=self.planned_path,
            completed_count=self.completed_count,
            total_count=self.total_count,
            message=self.status_message
        )

# Singleton Instance
mission_planner = MissionPlannerService()
