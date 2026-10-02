"""
Agriculture Manipulation Robot - A* (A-Star) Path Planning Engine
"""

import math
import heapq
from typing import List, Tuple, Dict, Any, Optional

from app.services.simulator import robot_state
from app.models import WaypointModel, PathPlanResponse

class AStarNode:
    def __init__(self, gx: int, gy: int, g: float = 0.0, h: float = 0.0, parent=None):
        self.gx = gx
        self.gy = gy
        self.g = g
        self.h = h
        self.f = g + h
        self.parent = parent

    def __lt__(self, other: 'AStarNode') -> bool:
        return self.f < other.f

class AStarPlanner:
    def __init__(self, cell_size: float = 20.0):
        self.field_width = 700.0   # 700 cm (7.0 m)
        self.field_height = 450.0  # 450 cm (4.5 m)
        self.cell_size = cell_size  # 20 cm grid resolution
        
        self.cols = int(math.ceil(self.field_width / self.cell_size))
        self.rows = int(math.ceil(self.field_height / self.cell_size))
        
        # Robot physical safety clearance (half chassis width + 10 cm buffer)
        self.robot_clearance = 30.0

    def world_to_grid(self, x: float, y: float) -> Tuple[int, int]:
        """Convert field world coordinates (cm) to grid indices (col, row)."""
        col = max(0, min(self.cols - 1, int(x / self.cell_size)))
        row = max(0, min(self.rows - 1, int(y / self.cell_size)))
        return col, row

    def grid_to_world(self, col: int, row: int) -> Tuple[float, float]:
        """Convert grid indices (col, row) to field world center coordinates (cm)."""
        x = col * self.cell_size + self.cell_size / 2.0
        y = row * self.cell_size + self.cell_size / 2.0
        return round(x, 1), round(y, 1)

    def is_valid_point(self, x: float, y: float) -> bool:
        """
        Check if a field world coordinate (x, y) is collision-free.
        Validates against field boundaries, rock obstacles, and plant row foliage.
        """
        half_w = self.robot_clearance
        # 1. Boundary check
        if x < half_w or x > (self.field_width - half_w):
            return False
        if y < half_w or y > (self.field_height - half_w):
            return False

        # 2. Rock obstacles check (with safety inflation margin)
        for obs in robot_state.obstacles:
            dist = math.hypot(x - obs.x, y - obs.y)
            if dist < (obs.radius + half_w):
                return False

        # 3. Dense crop row foliage check (Allow navigation through soil aisles and side headlands)
        # Headlands: x < 70 cm (left turn area) or x > 630 cm (right turn area)
        is_headland = (x < 70.0) or (x > 630.0)
        
        if not is_headland:
            for r in robot_state.plant_rows:
                # Row foliage region
                row_min_y = r["y"] - 12.0
                row_max_y = r["y"] + r["height"] + 12.0
                if row_min_y <= y <= row_max_y:
                    return False

        return True

    def find_nearest_valid_world_point(self, x: float, y: float) -> Tuple[float, float]:
        """If target is inside plant row/obstacle, find closest walkable point."""
        if self.is_valid_point(x, y):
            return x, y

        # Spiral search outward for nearest valid point
        for r in range(10, 120, 10):
            for angle_deg in range(0, 360, 30):
                rad = math.radians(angle_deg)
                nx = x + r * math.cos(rad)
                ny = y + r * math.sin(rad)
                if self.is_valid_point(nx, ny):
                    return round(nx, 1), round(ny, 1)

        return x, y

    def plan_path(self, start_x: float, start_y: float, goal_x: float, goal_y: float) -> PathPlanResponse:
        """
        Execute A* (A-Star) Path Finding Algorithm from Start (x,y) to Goal (x,y).
        Returns waypoints list, total distance, and status.
        """
        # Ensure start and goal are valid
        valid_start_x, valid_start_y = self.find_nearest_valid_world_point(start_x, start_y)
        valid_goal_x, valid_goal_y = self.find_nearest_valid_world_point(goal_x, goal_y)

        start_col, start_row = self.world_to_grid(valid_start_x, valid_start_y)
        goal_col, goal_row = self.world_to_grid(valid_goal_x, valid_goal_y)

        # A* Data Structures
        open_set: List[AStarNode] = []
        closed_set = set()

        start_node = AStarNode(
            start_col, start_row, 0.0, 
            math.hypot(valid_goal_x - valid_start_x, valid_goal_y - valid_start_y)
        )
        heapq.heappush(open_set, start_node)

        node_map: Dict[Tuple[int, int], AStarNode] = {(start_col, start_row): start_node}

        # 8-Directional Movement Vectors (dx, dy, step_cost)
        neighbors = [
            (1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0),
            (1, 1, 1.414), (1, -1, 1.414), (-1, 1, 1.414), (-1, -1, 1.414)
        ]

        found_node = None
        max_iterations = 2500
        iters = 0

        while open_set and iters < max_iterations:
            iters += 1
            current = heapq.heappop(open_set)

            if (current.gx, current.gy) in closed_set:
                continue

            closed_set.add((current.gx, current.gy))

            # Goal check (reached goal cell or close enough)
            if (current.gx == goal_col and current.gy == goal_row) or math.hypot(current.gx - goal_col, current.gy - goal_row) <= 1.2:
                found_node = current
                break

            cur_world_x, cur_world_y = self.grid_to_world(current.gx, current.gy)

            for dc, dr, cost in neighbors:
                nc, nr = current.gx + dc, current.gy + dr

                if not (0 <= nc < self.cols and 0 <= nr < self.rows):
                    continue
                if (nc, nr) in closed_set:
                    continue

                nw_x, nw_y = self.grid_to_world(nc, nr)
                if not self.is_valid_point(nw_x, nw_y):
                    continue

                new_g = current.g + cost * self.cell_size
                new_h = math.hypot(valid_goal_x - nw_x, valid_goal_y - nw_y)

                if (nc, nr) not in node_map or new_g < node_map[(nc, nr)].g:
                    neighbor_node = AStarNode(nc, nr, new_g, new_h, current)
                    node_map[(nc, nr)] = neighbor_node
                    heapq.heappush(open_set, neighbor_node)

        # Backtrack path
        raw_waypoints: List[WaypointModel] = []
        if found_node:
            curr = found_node
            while curr:
                wx, wy = self.grid_to_world(curr.gx, curr.gy)
                raw_waypoints.append(WaypointModel(x=wx, y=wy))
                curr = curr.parent
            raw_waypoints.reverse()

        # Always force start and goal precision
        if not raw_waypoints:
            raw_waypoints = [
                WaypointModel(x=round(valid_start_x, 1), y=round(valid_start_y, 1)),
                WaypointModel(x=round(valid_goal_x, 1), y=round(valid_goal_y, 1))
            ]

        # Simplify path (remove collinear grid points)
        simplified = self.simplify_waypoints(raw_waypoints)

        # Compute total path distance
        total_dist = 0.0
        for i in range(len(simplified) - 1):
            total_dist += math.hypot(simplified[i+1].x - simplified[i].x, simplified[i+1].y - simplified[i].y)

        return PathPlanResponse(
            success=True,
            algorithm="A* (A-Star)",
            start=WaypointModel(x=round(start_x, 1), y=round(start_y, 1)),
            goal=WaypointModel(x=round(goal_x, 1), y=round(goal_y, 1)),
            waypoints=simplified,
            total_distance_cm=round(total_dist, 1),
            message=f"A* path planned successfully ({len(simplified)} waypoints, {total_dist:.1f} cm total)."
        )

    def simplify_waypoints(self, waypoints: List[WaypointModel]) -> List[WaypointModel]:
        """Compress dense grid waypoints by dropping intermediate collinear points."""
        if len(waypoints) <= 2:
            return waypoints

        simplified = [waypoints[0]]
        for i in range(1, len(waypoints) - 1):
            prev = simplified[-1]
            curr = waypoints[i]
            next_pt = waypoints[i+1]

            # Calculate direction vectors
            dir1_x, dir1_y = curr.x - prev.x, curr.y - prev.y
            dir2_x, dir2_y = next_pt.x - curr.x, next_pt.y - curr.y

            angle1 = math.atan2(dir1_y, dir1_x)
            angle2 = math.atan2(dir2_y, dir2_x)

            # Keep waypoint if direction changes significantly
            if abs(angle1 - angle2) > 0.08:
                simplified.append(curr)

        simplified.append(waypoints[-1])
        return simplified

# Singleton Instance
path_planner = AStarPlanner()
