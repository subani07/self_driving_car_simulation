"""
perception.py
─────────────
OpenCV-based perception pipeline.

Produces:
  • lane_offset  – how far the car's centre is from the lane centre (px)
  • steer_angle  – recommended steering correction (degrees)
  • cv_boxes     – detected real-world objects
  • debug_frame  – annotated BGR frame
"""

import cv2
import numpy as np
import config as C

class PIDController:
    def __init__(self, kp, ki, kd):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.prev_error = 0.0
        self.integral = 0.0

    def compute(self, error: float) -> float:
        self.integral += error
        # Anti-windup for integral
        self.integral = max(-500, min(500, self.integral))
        derivative = error - self.prev_error
        self.prev_error = error
        return self.kp * error + self.ki * self.integral + self.kd * derivative

ROI_TOP = int(C.SCREEN_HEIGHT * C.ROI_TOP_RATIO)

class Perception:
    def __init__(self):
        self.prev_left_x  : float | None = None
        self.prev_right_x : float | None = None
        self._alpha = 0.25
        
        # Initialize PID for steering calculations
        # Restored stable Kp/Ki/Kd values
        self.steering_pid = PIDController(kp=0.10, ki=0.001, kd=0.05)

        self.last_cv_boxes = []

    def process(self, rgb_frame: np.ndarray, car_x: float) -> dict:
        bgr = cv2.cvtColor(rgb_frame, cv2.COLOR_RGB2BGR)
        debug = bgr.copy()

        # ── 1. Simulated Object Detection (OpenCV) ───────────
        boxes = []
            
        # Pedestrian Detection
        ped_mask = cv2.inRange(bgr, np.array([195, 45, 45]), np.array([205, 55, 55]))
        cnts, _ = cv2.findContours(ped_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for c in cnts:
            if cv2.contourArea(c) > 10:
                x, y, w, h = cv2.boundingRect(c)
                boxes.append({'name': 'person', 'rect': [x, y-10, 30, 30], 'cx': x+15, 'cy': y+5, 'bottom': y+20})

        # Car Detection 
        car_mask = cv2.inRange(bgr, np.array([45, 45, 215]), np.array([55, 55, 225]))
        cnts, _ = cv2.findContours(car_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for c in cnts:
            if cv2.contourArea(c) > 50:
                x, y, w, h = cv2.boundingRect(c)
                boxes.append({'name': 'car', 'rect': [x, y, 40, 70], 'cx': x+20, 'cy': y+35, 'bottom': y+70})

        # Traffic Light Detection 
        red_mask = cv2.inRange(bgr, np.array([0, 0, 250]), np.array([10, 10, 255]))
        cnts, _ = cv2.findContours(red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for c in cnts:
            if cv2.contourArea(c) > 5:
                x, y, w, h = cv2.boundingRect(c)
                boxes.append({'name': 'red_light', 'rect': [x-4, y-4, 20, 60], 'cx': x+6, 'cy': y+26, 'bottom': y+56})

        self.last_cv_boxes = boxes

        # Annotate Boxes
        for b in self.last_cv_boxes:
            rx, ry, rw, rh = b['rect']
            col = (0, 0, 255) if b['name'] in ['person', 'red_light'] else (255, 0, 0)
            cv2.rectangle(debug, (rx, ry), (rx+rw, ry+rh), col, 2)
            cv2.putText(debug, b['name'], (rx, ry-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, col, 2)

        # ── 2. Lane Detection ────────
        roi = bgr[ROI_TOP:, C.ROAD_LEFT:C.ROAD_RIGHT]
        mask = self._colour_mask(roi)
        blur  = cv2.GaussianBlur(mask, (5, 5), 0)
        edges = cv2.Canny(blur, 50, 150)
        lines = cv2.HoughLinesP(edges, rho=1, theta=np.pi/180, threshold=C.HOUGH_THRESHOLD, minLineLength=C.HOUGH_MIN_LENGTH, maxLineGap=C.HOUGH_MAX_GAP)

        left_x, right_x = self._find_lane_edges(lines, roi.shape[1])
        left_x  = self._ema(left_x,  self.prev_left_x)
        right_x = self._ema(right_x, self.prev_right_x)

        self.prev_left_x, self.prev_right_x = left_x, right_x

        if left_x is not None and right_x is not None:
            detected_centre = (left_x + right_x) / 2 + C.ROAD_LEFT
        elif left_x is not None: detected_centre = left_x + C.LANE_WIDTH + C.ROAD_LEFT
        elif right_x is not None: detected_centre = right_x - C.LANE_WIDTH + C.ROAD_LEFT
        else: detected_centre = C.LANE_CENTER

        lane_offset = detected_centre - car_x
        raw_steer = self.steering_pid.compute(lane_offset)
        steer_angle = max(-C.MAX_STEER, min(C.MAX_STEER, raw_steer))

        self._annotate(debug, left_x, right_x, detected_centre, lane_offset)

        return {
            "lane_offset"  : lane_offset,
            "steer_angle"  : steer_angle,
            "cv_boxes"     : self.last_cv_boxes,
            "debug_frame"  : debug,
        }

    # ── Helpers ──────────────

    @staticmethod
    def _colour_mask(bgr_roi: np.ndarray) -> np.ndarray:
        hsv = cv2.cvtColor(bgr_roi, cv2.COLOR_BGR2HSV)
        white_m = cv2.inRange(hsv, np.array([0, 0, 180]), np.array([180, 30, 255]))
        yellow_m = cv2.inRange(hsv, np.array([15, 80, 100]), np.array([40, 255, 255]))
        return cv2.bitwise_or(white_m, yellow_m)

    @staticmethod
    def _find_lane_edges(lines, roi_width: int):
        left_xs, right_xs = [], []
        if lines is None: return None, None
        mid = roi_width / 2
        for line in lines:
            x1, y1, x2, y2 = line[0]
            if abs(y2 - y1) < 10: continue
            cx = (x1 + x2) / 2
            if cx < mid: left_xs.append(cx)
            else: right_xs.append(cx)
        return (float(np.median(left_xs)) if left_xs else None, float(np.median(right_xs)) if right_xs else None)

    def _ema(self, new_val, prev_val):
        if new_val is None: return prev_val
        if prev_val is None: return new_val
        return self._alpha * new_val + (1 - self._alpha) * prev_val

    def _annotate(self, frame, left_x, right_x, detected_centre, lane_offset):
        h, w = frame.shape[:2]
        if left_x:
            cv2.line(frame, (int(left_x + C.ROAD_LEFT), ROI_TOP), (int(left_x + C.ROAD_LEFT), h), (0, 255, 0), 2)
        if right_x:
            cv2.line(frame, (int(right_x + C.ROAD_LEFT), ROI_TOP), (int(right_x + C.ROAD_LEFT), h), (0, 255, 0), 2)
        
        cv2.line(frame, (int(detected_centre), ROI_TOP), (int(detected_centre), h), (0, 200, 255), 2)
        cv2.putText(frame, f"Offset: {lane_offset:+.1f} px", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 0), 2)
