"""
Agriculture Manipulation Robot - Computer Vision Pipeline & Target Detection Engine
"""

import math
import base64
import cv2
import numpy as np
from typing import List, Dict, Any, Optional

from app.services.simulator import robot_state
from app.models import DetectedFruitObject, VisionDetectionResponse, HSVThresholdCommand

class FruitDetectorService:
    def __init__(self):
        self.active: bool = True
        self.target_fruit_id: Optional[str] = "fruit_1"  # Default lock on Target 1 (Ripe Red Apple)
        
        # Adjustable HSV Color Threshold Parameters
        self.hsv_params = {
            "red_lower1": np.array([0, 90, 90]),
            "red_upper1": np.array([12, 255, 255]),
            "red_lower2": np.array([160, 90, 90]),
            "red_upper2": np.array([180, 255, 255]),
            "yellow_lower": np.array([18, 90, 90]),
            "yellow_upper": np.array([35, 255, 255]),
            "green_lower": np.array([35, 60, 60]),
            "green_upper": np.array([85, 255, 255])
        }

        # Camera Pinhole Model Geometry
        self.img_width = 640
        self.img_height = 480
        self.fov_degrees = 60.0
        self.focal_length = (self.img_width / 2.0) / math.tan(math.radians(self.fov_degrees / 2.0))

    def update_hsv_thresholds(self, cmd: HSVThresholdCommand):
        """Update HSV color filter ranges dynamically."""
        self.hsv_params["red_lower1"] = np.array([cmd.h_min, cmd.s_min, cmd.v_min])
        self.hsv_params["red_upper1"] = np.array([cmd.h_max, cmd.s_max, cmd.v_max])

    def set_target_fruit(self, fruit_id: str) -> Dict[str, Any]:
        """Lock vision target onto a specific fruit ID."""
        self.target_fruit_id = fruit_id
        robot_state.mission_state = f"TARGET_LOCKED ({fruit_id})"
        return {"target_fruit_id": fruit_id, "status": "locked"}

    def map_image_to_world_coords(self, img_x: int, bbox_w: int, robot_pose: Any) -> Dict[str, float]:
        """
        Convert 2D camera image coordinates into 2D Field World coordinates (cm).
        Uses camera pinhole focal geometry and robot pose transformation.
        """
        # Calculate angle offset relative to camera optical center (px)
        offset_x = img_x - (self.img_width / 2.0)
        angle_offset_deg = math.degrees(math.atan2(offset_x, self.focal_length))
        
        # Global ray angle in field world
        world_angle_deg = (robot_pose.heading + angle_offset_deg) % 360.0
        rad = math.radians(world_angle_deg)

        # Estimate distance from bounding box width (larger bbox -> closer fruit)
        known_fruit_diameter_cm = 28.0
        estimated_dist_cm = max(15.0, min(300.0, (known_fruit_diameter_cm * self.focal_length) / max(1.0, float(bbox_w))))

        # Compute field world coordinates
        field_x = round(robot_pose.x + estimated_dist_cm * math.cos(rad), 1)
        field_y = round(robot_pose.y + estimated_dist_cm * math.sin(rad), 1)

        return {
            "field_x": field_x,
            "field_y": field_y,
            "distance_cm": round(estimated_dist_cm, 1)
        }

    def render_simulated_camera_frame(self) -> np.ndarray:
        """
        Synthesize a realistic camera frame as perceived by the robot's front-facing USB camera.
        Renders field ground, crop rows, and fruits in view.
        """
        # Create dark background frame (640x480)
        frame = np.zeros((self.img_height, self.img_width, 3), dtype=np.uint8)
        
        # Ground texture (Dark green / brown field background)
        frame[:] = (35, 55, 30)

        # Draw horizon line / plant canopy background
        cv2.rectangle(frame, (0, 0), (self.img_width, 140), (20, 80, 25), -1)

        robot_pose = robot_state.pose

        # Project field fruits into camera frame coordinates
        for fruit in robot_state.fruits:
            if fruit.picked:
                continue

            dx = fruit.x - robot_pose.x
            dy = fruit.y - robot_pose.y
            dist = math.hypot(dx, dy)

            if dist > 350.0:  # Beyond camera view cutoff
                continue

            # Calculate relative angle from robot heading
            angle_to_fruit = math.degrees(math.atan2(dy, dx))
            angle_diff = (angle_to_fruit - robot_pose.heading + 180) % 360 - 180

            # Check if within camera 60-degree FOV cone in front of robot
            if abs(angle_diff) <= (self.fov_degrees / 2.0) and dist > 10.0:
                # Project angle diff onto screen X axis
                img_x = int((self.img_width / 2.0) + self.focal_length * math.tan(math.radians(angle_diff)))
                
                # Project distance onto screen Y axis (closer items appear lower)
                img_y = int(240 + (12000.0 / dist))
                radius_px = int(max(8, min(65, (fruit.radius * self.focal_length) / dist)))

                # Draw raw synthetic fruit circle in frame before OpenCV color pipeline runs
                color_bgr = (50, 50, 220) if "#e53935" in fruit.color else ((50, 220, 240) if "#fdd835" in fruit.color else (60, 180, 60))
                cv2.circle(frame, (img_x, img_y), radius_px, color_bgr, -1)
                cv2.circle(frame, (img_x - int(radius_px * 0.3), img_y - int(radius_px * 0.3)), int(radius_px * 0.25), (255, 255, 255), -1)

        return frame

    def run_detection_pipeline(self) -> VisionDetectionResponse:
        """
        Execute full OpenCV Fruit Target Detection & Bounding Box Localization pipeline.
        Processes camera frame, extracts HSV color masks, detects contours, maps coordinates,
        and annotates bounding boxes & confidence scores.
        """
        if not self.active:
            return VisionDetectionResponse(
                success=True,
                active=False,
                detected_count=0,
                target_fruit_id=self.target_fruit_id,
                camera_frame_b64="",
                objects=[],
                message="Vision pipeline is currently PAUSED"
            )

        # 1. Synthesize / Read camera frame
        frame = self.render_simulated_camera_frame()

        # 2. Convert BGR image to HSV color space
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # 3. Apply HSV Color Threshold Segmentation
        mask_red1 = cv2.inRange(hsv, self.hsv_params["red_lower1"], self.hsv_params["red_upper1"])
        mask_red2 = cv2.inRange(hsv, self.hsv_params["red_lower2"], self.hsv_params["red_upper2"])
        mask_red = cv2.bitwise_or(mask_red1, mask_red2)

        mask_yellow = cv2.inRange(hsv, self.hsv_params["yellow_lower"], self.hsv_params["yellow_upper"])
        mask_green = cv2.inRange(hsv, self.hsv_params["green_lower"], self.hsv_params["green_upper"])

        detected_objects: List[DetectedFruitObject] = []
        robot_pose = robot_state.pose

        categories = [
            ("Ripe Red Apple", mask_red, True),
            ("Yellow Lemon", mask_yellow, True),
            ("Unripe Green Fruit", mask_green, False)
        ]

        # 4. Contour Analysis & Bounding Box Extraction
        for label_text, mask, is_ripe in categories:
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for cnt in contours:
                area = cv2.contourArea(cnt)
                if area < 40.0:  # Noise filter
                    continue

                x, y, w, h = cv2.boundingRect(cnt)
                cx = x + w // 2
                cy = y + h // 2

                # Calculate contour circularity for confidence scoring
                perimeter = cv2.arcLength(cnt, True)
                circularity = (4.0 * math.pi * area) / (perimeter * perimeter) if perimeter > 0 else 0.8
                confidence = round(min(0.99, max(0.75, circularity * 0.95 + 0.1)), 2)

                # Map 2D pixel coordinates to 2D field world coordinates
                mapping = self.map_image_to_world_coords(cx, w, robot_pose)

                # Match with closest unpicked field fruit to preserve fruit ID
                matched_id = "fruit_target"
                min_match_dist = 999.0
                for f in robot_state.fruits:
                    if not f.picked:
                        dist_f = math.hypot(f.x - mapping["field_x"], f.y - mapping["field_y"])
                        if dist_f < min_match_dist:
                            min_match_dist = dist_f
                            matched_id = f.id

                is_target = (matched_id == self.target_fruit_id)

                obj = DetectedFruitObject(
                    fruit_id=matched_id,
                    label=label_text,
                    confidence=confidence,
                    bbox=[x, y, w, h],
                    center_img=[cx, cy],
                    field_x=mapping["field_x"],
                    field_y=mapping["field_y"],
                    is_target=is_target,
                    is_ripe=is_ripe,
                    distance_cm=mapping["distance_cm"]
                )
                detected_objects.append(obj)

                # 5. Draw Bounding Boxes, Labels & Target Reticles on Camera Frame
                box_color = (0, 0, 255) if is_target else ((0, 255, 0) if is_ripe else (100, 200, 100))

                # Draw Bounding Box Rectangle
                cv2.rectangle(frame, (x, y), (x + w, y + h), box_color, 2 if not is_target else 3)

                # Target Lock Crosshairs if selected
                if is_target:
                    cv2.line(frame, (cx - 12, cy), (cx + 12, cy), (0, 255, 255), 2)
                    cv2.line(frame, (cx, cy - 12), (cx, cy + 12), (0, 255, 255), 2)
                    cv2.putText(frame, "TARGET LOCK", (x, y - 18), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 2)

                # Class Label & Confidence Banner
                tag = f"{label_text} {int(confidence * 100)}%"
                cv2.rectangle(frame, (x, y - 16), (x + len(tag) * 8 + 4, y), box_color, -1)
                cv2.putText(frame, tag, (x + 2, y - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)

                # Mapped Distance Tag below box
                cv2.putText(frame, f"Dist:{mapping['distance_cm']}cm (X:{mapping['field_x']},Y:{mapping['field_y']})", 
                            (x, y + h + 12), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 255, 200), 1)

        # Draw HUD overlay on camera frame
        cv2.putText(frame, f"OpenCV DETECTED: {len(detected_objects)} TARGETS", (15, 460), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        cv2.putText(frame, f"ACTIVE TARGET: {self.target_fruit_id or 'NONE'}", (380, 460), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

        # 6. Encode Frame to JPEG Base64
        _, buffer = cv2.imencode('.jpg', frame)
        frame_b64 = "data:image/jpeg;base64," + base64.b64encode(buffer).decode('utf-8')

        return VisionDetectionResponse(
            success=True,
            active=True,
            detected_count=len(detected_objects),
            target_fruit_id=self.target_fruit_id,
            camera_frame_b64=frame_b64,
            objects=detected_objects,
            message=f"Detected {len(detected_objects)} fruit targets in real-time."
        )

    def navigate_towards_target(self) -> Dict[str, Any]:
        """
        Autonomous Closed-Loop Proportional Navigation Control.
        Steers robot toward selected target fruit and executes automatic pick when within reach.
        """
        if not self.target_fruit_id:
            return {"status": "failed", "message": "No target fruit selected for navigation!"}

        target_fruit = None
        for f in robot_state.fruits:
            if f.id == self.target_fruit_id and not f.picked:
                target_fruit = f
                break

        if not target_fruit:
            return {"status": "failed", "message": f"Target fruit '{self.target_fruit_id}' is already picked or not found!"}

        pose = robot_state.pose
        dx = target_fruit.x - pose.x
        dy = target_fruit.y - pose.y
        dist = math.hypot(dx, dy)

        # Target angle in degrees
        target_angle_deg = math.degrees(math.atan2(dy, dx)) % 360.0
        angle_err = (target_angle_deg - pose.heading + 180) % 360 - 180

        # Steer toward target if heading error > 5 degrees
        if abs(angle_err) > 5.0:
            turn_rate = max(-60.0, min(60.0, angle_err * 3.0))
            robot_state.angular_velocity = turn_rate
            robot_state.linear_velocity = 0.0
            robot_state.step(0.2, force=True)
            robot_state.mission_state = f"ALIGNING_TO_TARGET ({angle_err:.1f}°)"
            return {
                "status": "aligning",
                "message": f"Aligning robot heading toward target fruit ({angle_err:.1f}° error).",
                "distance_cm": round(dist, 1)
            }
        elif dist > 55.0:
            # Drive forward toward target fruit
            robot_state.linear_velocity = max(30.0, min(60.0, dist * 0.8))
            robot_state.angular_velocity = 0.0
            robot_state.step(0.2, force=True)
            robot_state.mission_state = f"APPROACHING_TARGET ({dist:.1f} cm)"
            return {
                "status": "approaching",
                "message": f"Approaching target fruit (Distance: {dist:.1f} cm).",
                "distance_cm": round(dist, 1)
            }
        else:
            # Robot reached picking radius! Stop chassis and harvest fruit
            robot_state.linear_velocity = 0.0
            robot_state.angular_velocity = 0.0
            pick_res = robot_state.pick_nearest_fruit()
            robot_state.mission_state = "HARVEST_COMPLETE"
            return {
                "status": "harvested",
                "message": pick_res.get("message", "Target fruit successfully harvested!"),
                "result": pick_res
            }


# Singleton Instance
vision_service = FruitDetectorService()
