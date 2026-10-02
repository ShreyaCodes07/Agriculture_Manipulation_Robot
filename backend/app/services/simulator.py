"""
Agriculture Manipulation Robot - 2D Field Physics & Environment Simulator
"""

import math
from typing import List, Dict, Any
from app.config import settings
from app.models import ArmCommand, RobotPose, SensorData, RobotStatusResponse

class FieldFruit:
    def __init__(self, fruit_id: str, label: str, x: float, y: float, color: str, radius: float = 12.0):
        self.id = fruit_id
        self.label = label
        self.x = x
        self.y = y
        self.color = color
        self.radius = radius
        self.picked = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "x": self.x,
            "y": self.y,
            "color": self.color,
            "radius": self.radius,
            "picked": self.picked
        }

class FieldObstacle:
    def __init__(self, obs_id: str, label: str, x: float, y: float, radius: float = 22.0):
        self.id = obs_id
        self.label = label
        self.x = x
        self.y = y
        self.radius = radius

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "x": self.x,
            "y": self.y,
            "radius": self.radius
        }

class AgriculturalFieldSimulator:
    def __init__(self):
        self.field_width = 700.0   # 7.0 meters (700 cm)
        self.field_height = 450.0  # 4.5 meters (450 cm)
        
        # State Control Flags
        self.running: bool = False
        self.speed_multiplier: float = 1.0
        self.operation_mode: str = settings.MODE.upper()  # "SIMULATION" or "HARDWARE"
        self.control_mode: str = "MANUAL"                   # "MANUAL" or "AUTONOMOUS"
        self.estop_engaged: bool = False
        self.mission_state: str = "IDLE"

        # Robot Physical Model
        self.pose = RobotPose(x=80.0, y=160.0, heading=0.0)
        self.chassis_width = 40.0   # 40 cm width
        self.chassis_length = 50.0  # 50 cm length
        self.linear_velocity = 0.0  # cm/s
        self.angular_velocity = 0.0 # deg/s

        # Robotic Arm & End-Effector
        self.arm = ArmCommand(theta_base=90.0, theta_shoulder=45.0, theta_elbow=30.0, theta_wrist=0.0)
        self.gripper_state: str = "OPEN"

        # Sensor Telemetry
        self.sensors = SensorData(distance_cm=85.0, soil_moisture_percent=45.0, obstacle_warning=False)

        # Onboard Collection Basket
        self.basket_capacity = 10
        self.basket_items: List[str] = []

        # Field Layout Environment Objects
        self.fruits: List[FieldFruit] = []
        self.obstacles: List[FieldObstacle] = []
        self.plant_rows: List[Dict[str, Any]] = []

        self.reset_environment()

    def reset_environment(self):
        """Reset robot pose, fruits, obstacles, and basket back to initial state."""
        self.pose = RobotPose(x=80.0, y=160.0, heading=0.0)
        self.linear_velocity = 0.0
        self.angular_velocity = 0.0
        self.arm = ArmCommand(theta_base=90.0, theta_shoulder=45.0, theta_elbow=30.0, theta_wrist=0.0)
        self.gripper_state = "OPEN"
        self.estop_engaged = False
        self.mission_state = "IDLE"
        self.basket_items = []
        self.running = False

        # Crop Rows Geometry
        self.plant_rows = [
            {"id": "row_1", "y": 100.0, "height": 35.0, "label": "Tomato Row 1"},
            {"id": "row_2", "y": 220.0, "height": 35.0, "label": "Apple Orchard Row 2"},
            {"id": "row_3", "y": 340.0, "height": 35.0, "label": "Citrus Lemon Row 3"}
        ]

        # Field Fruits
        self.fruits = [
            FieldFruit("fruit_1", "Ripe Red Apple", 180.0, 95.0, "#e53935", 14.0),
            FieldFruit("fruit_2", "Ripe Red Apple", 380.0, 95.0, "#e53935", 14.0),
            FieldFruit("fruit_3", "Yellow Lemon", 260.0, 215.0, "#fdd835", 12.0),
            FieldFruit("fruit_4", "Ripe Red Apple", 480.0, 215.0, "#e53935", 14.0),
            FieldFruit("fruit_5", "Yellow Lemon", 320.0, 335.0, "#fdd835", 12.0),
            FieldFruit("fruit_6", "Unripe Green Fruit", 560.0, 335.0, "#4caf50", 12.0)
        ]

        # Field Rocks / Obstacles
        self.obstacles = [
            FieldObstacle("obs_1", "Rock Obstacle A", 280.0, 160.0, 22.0),
            FieldObstacle("obs_2", "Rock Obstacle B", 440.0, 280.0, 25.0)
        ]

        self.update_sensors()

    def update_sensors(self):
        """Compute forward ultrasonic raycast distance to nearest obstacle/wall and soil moisture."""
        if self.estop_engaged:
            self.sensors.obstacle_warning = True
            return

        # Ultrasonic forward Raycast simulation along heading angle
        rad = math.radians(self.pose.heading)
        dx = math.cos(rad)
        dy = math.sin(rad)

        min_distance = 300.0  # Max ultrasonic range cutoff (300 cm)

        # Distance to field boundary walls
        if dx > 0:
            dist_wall_x = (self.field_width - self.pose.x) / dx
        elif dx < 0:
            dist_wall_x = -self.pose.x / dx
        else:
            dist_wall_x = 999.0

        if dy > 0:
            dist_wall_y = (self.field_height - self.pose.y) / dy
        elif dy < 0:
            dist_wall_y = -self.pose.y / dy
        else:
            dist_wall_y = 999.0

        min_distance = min(min_distance, max(0.0, dist_wall_x), max(0.0, dist_wall_y))

        # Distance to obstacles
        for obs in self.obstacles:
            ox = obs.x - self.pose.x
            oy = obs.y - self.pose.y
            dist_center = math.hypot(ox, oy)
            
            # Check projection along heading ray
            proj = ox * dx + oy * dy
            if proj > 0:  # In front of robot
                perp_dist = abs(-ox * dy + oy * dx)
                if perp_dist <= obs.radius + (self.chassis_width / 2.0):
                    hit_dist = proj - obs.radius
                    if hit_dist < min_distance:
                        min_distance = max(0.0, hit_dist)

        self.sensors.distance_cm = round(min_distance, 1)
        self.sensors.obstacle_warning = self.sensors.distance_cm < 30.0

        # Dynamic Soil Moisture Model based on Y coordinate path
        base_moisture = 42.0 + 8.0 * math.sin(self.pose.x / 100.0) + 5.0 * math.cos(self.pose.y / 80.0)
        self.sensors.soil_moisture_percent = round(max(10.0, min(95.0, base_moisture)), 1)

    def step(self, delta_time: float = 0.1, force: bool = False):
        """Advance physics simulation by delta_time seconds."""
        if self.estop_engaged:
            return

        if not self.running and not force:
            return

        effective_dt = delta_time * self.speed_multiplier

        # Update Heading Angle
        self.pose.heading = (self.pose.heading + self.angular_velocity * effective_dt) % 360.0

        # Update Position
        rad = math.radians(self.pose.heading)
        new_x = self.pose.x + self.linear_velocity * math.cos(rad) * effective_dt
        new_y = self.pose.y + self.linear_velocity * math.sin(rad) * effective_dt

        # Check collision with field boundaries
        half_w = self.chassis_width / 2.0
        new_x = max(half_w, min(self.field_width - half_w, new_x))
        new_y = max(half_w, min(self.field_height - half_w, new_y))

        # Check collision with obstacles
        collision = False
        for obs in self.obstacles:
            dist = math.hypot(new_x - obs.x, new_y - obs.y)
            if dist < (obs.radius + half_w):
                collision = True
                break

        if not collision:
            self.pose.x = round(new_x, 2)
            self.pose.y = round(new_y, 2)
        else:
            self.linear_velocity = 0.0

        self.update_sensors()

    def drive(self, direction: str, speed: float = 1.0):
        """Apply teleoperation motor control vectors."""
        if self.estop_engaged:
            return

        speed_cm_s = 40.0 * speed  # 40 cm/s base speed

        if direction == "forward":
            if self.sensors.distance_cm < 30.0:
                self.linear_velocity = 0.0
                return
            self.linear_velocity = speed_cm_s
            self.angular_velocity = 0.0
        elif direction == "backward":
            self.linear_velocity = -speed_cm_s
            self.angular_velocity = 0.0
        elif direction == "left":
            self.linear_velocity = 0.0
            self.angular_velocity = -45.0  # -45 deg/s left turn
        elif direction == "right":
            self.linear_velocity = 0.0
            self.angular_velocity = 45.0   # +45 deg/s right turn
        elif direction == "stop":
            self.linear_velocity = 0.0
            self.angular_velocity = 0.0

    def pick_nearest_fruit(self) -> Dict[str, Any]:
        """Harvest closest unpicked fruit within 60 cm reach of the robot."""
        if self.estop_engaged:
            return {"success": False, "message": "Harvest blocked: EMERGENCY STOP is ENGAGED!"}

        nearest_fruit = None
        min_dist = 999.0

        for fruit in self.fruits:
            if not fruit.picked:
                dist = math.hypot(fruit.x - self.pose.x, fruit.y - self.pose.y)
                if dist < min_dist:
                    min_dist = dist
                    nearest_fruit = fruit

        reach_threshold = 65.0  # 65 cm reach radius
        if nearest_fruit and min_dist <= reach_threshold:
            if "Unripe" in nearest_fruit.label or nearest_fruit.color == "#4caf50":
                return {
                    "success": False,
                    "message": f"Harvest rejected: '{nearest_fruit.label}' is unripe! Color vision filter blocked picking.",
                    "fruit": nearest_fruit.to_dict()
                }

            if len(self.basket_items) >= self.basket_capacity:
                return {
                    "success": False,
                    "message": f"Harvest failed: Onboard basket is FULL ({len(self.basket_items)}/{self.basket_capacity})!"
                }

            nearest_fruit.picked = True
            self.basket_items.append(nearest_fruit.label)
            self.mission_state = "FRUIT_HARVESTED"
            self.gripper_state = "CLOSE"

            return {
                "success": True,
                "message": f"Successfully picked '{nearest_fruit.label}'! Placed in basket ({len(self.basket_items)}/{self.basket_capacity}).",
                "fruit": nearest_fruit.to_dict(),
                "basket_count": len(self.basket_items)
            }
        else:
            dist_info = f"({min_dist:.1f} cm away)" if nearest_fruit else ""
            return {
                "success": False,
                "message": f"No unpicked fruit within arm reach (65 cm) {dist_info}. Move closer!"
            }

    def get_world_snapshot(self) -> Dict[str, Any]:
        return {
            "field": {
                "width": self.field_width,
                "height": self.field_height,
                "rows": self.plant_rows
            },
            "robot": self.get_status().model_dump(),
            "fruits": [f.to_dict() for f in self.fruits],
            "obstacles": [o.to_dict() for o in self.obstacles],
            "basket": {
                "capacity": self.basket_capacity,
                "count": len(self.basket_items),
                "items": self.basket_items
            },
            "sim_status": {
                "running": self.running,
                "speed_multiplier": self.speed_multiplier
            }
        }

    def get_status(self) -> RobotStatusResponse:
        return RobotStatusResponse(
            operation_mode=self.operation_mode,
            control_mode=self.control_mode,
            estop_engaged=self.estop_engaged,
            pose=self.pose,
            arm=self.arm,
            gripper_state=self.gripper_state,
            sensors=self.sensors,
            mission_state=self.mission_state
        )

# Global Singleton Instance
robot_state = AgriculturalFieldSimulator()

