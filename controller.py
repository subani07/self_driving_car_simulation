"""
controller.py
─────────────
Autonomous driving controller.

Reads CV perception output + lane data and decides:
  • steering angle for the car
  • speed (accelerate / brake)
  • alert level (SAFE, WARNING, DANGER, COLLISION)
"""

import config as C


class AlertLevel:
    SAFE      = "SAFE"
    WARNING   = "WARNING"
    DANGER    = "DANGER"
    COLLISION = "COLLISION"


class Controller:
    def __init__(self):
        self.alert        = AlertLevel.SAFE
        self.nearest_dist = float("inf")
        self.is_fused     = False
        self.evasion_timer = 0
        self.evasion_direction = 0

    def decide(self, car, perception_data: dict, obstacles: list) -> None:
        steer_angle  = perception_data["steer_angle"]
        cv_boxes     = perception_data.get("cv_boxes", [])

        self.nearest_dist = float("inf")
        fused_target = None
        
        car_top = car.rect.top

        # ── 1. Simulated LIDAR (Ground Truth Distances) ──
        lidar_data = []
        for obs in obstacles:
            # Ignore green lights
            if obs.obs_type == 'traffic_light' and obs.state == 'green':
                continue
            
            # Ground truth distance
            dy = car_top - obs.rect.bottom
            if dy < -40:  # Passed us
                continue
                
            # ── ADD LIDAR SENSOR NOISE ──
            # +/- ~5px random jitter to simulate inaccurate LIDAR bounces
            import random
            noise = random.gauss(0, 5.0)
            dy_noisy = max(0.0, dy + noise)
                
            cx = obs.x + (obs.w / 2)
            dx = cx - car.x
            
            # Is the object actually in our physical path?
            # We check if horizontal overlap exceeds the physical widths + a 15px safety margin
            in_path = abs(dx) < (C.CAR_WIDTH / 2 + obs.w / 2 + 15)
            
            if obs.obs_type == 'car':
                # Trigger evasion if the car breaches our outer visual perception frame (85px)
                if abs(dx) < 85:
                    in_path = True
                    
            # Traffic lights strictly apply to the entire road
            if obs.obs_type == 'traffic_light':
                in_path = True
                
            # Pedestrians cross the road laterally, so they have a significantly larger detection width.
            # We want to brake if they are approaching our lane, not just when they step directly on our hood.
            if obs.obs_type == 'pedestrian':
                if abs(dx) < 140:
                    in_path = True
                
            lidar_data.append({
                'name': obs.obs_type,
                'dy': dy_noisy,
                'cx': cx,
                'in_path': in_path
            })

        # ── 2. Sensor Fusion ──
        # Merge accurate LIDAR range with CV object recognition
        self.is_fused = False
        for l_obj in lidar_data:
            if not l_obj['in_path']:
                continue
                
            # Perform fusion: Check if CV saw it
            cv_verified = False
            for box in cv_boxes:
                # Spatial matching: are the centers close?
                if abs(box['cx'] - l_obj['cx']) < 40:
                    cv_verified = True
                    break
                    
            if l_obj['dy'] < self.nearest_dist:
                self.nearest_dist = l_obj['dy']
                fused_target = l_obj
                fused_target['cv_verified'] = cv_verified
                self.is_fused = cv_verified

        # ── 3. Determine alert level ──────────────
        if self.nearest_dist <= 10:
            self.alert = AlertLevel.COLLISION
        elif self.nearest_dist < C.DANGER_DISTANCE:
            self.alert = AlertLevel.DANGER
        elif self.nearest_dist < C.WARNING_DISTANCE:
            self.alert = AlertLevel.WARNING
        else:
            self.alert = AlertLevel.SAFE

        # ── 4. Speed control ──────────────────────
        # Override for persons and red lights -> force hard brake
        if fused_target and fused_target['name'] in ['pedestrian', 'traffic_light'] and self.alert != AlertLevel.SAFE:
            car.brake() # They get priority braking
        elif self.alert in (AlertLevel.DANGER, AlertLevel.COLLISION):
            car.brake()
        else:
            car.accelerate()

        # ── 5. Steering: lane-keeping + evasion ──
        if self.alert in (AlertLevel.DANGER, AlertLevel.COLLISION) and fused_target is not None and fused_target['name'] == 'car':
            obs_cx = fused_target['cx']
            
            # Apply a sustained evasion buffer so the car completely clears the obstacle and handles the lane-change smoothly
            self.evasion_timer = 40  # Frames to sustain lateral evasion
            if obs_cx > car.x:       # Obstacle is to our right
                self.evasion_direction = -1  # Swerve left
            else:
                self.evasion_direction = 1   # Swerve right

        if self.evasion_timer > 0:
            self.evasion_timer -= 1
            # Heavily prioritize evasion over lane tracking
            evade = self.evasion_direction * C.MAX_STEER * 0.90
            blend = 0.85 * evade + 0.15 * steer_angle
            car.set_steer_direct(blend)
        else:
            car.set_steer_direct(steer_angle)

    def get_status(self) -> dict:
        return {
            "alert"        : self.alert,
            "nearest_dist" : self.nearest_dist,
            "is_fused"     : self.is_fused,
        }
