"""
environment.py
──────────────
Pygame-based simulation environment:
  • Scrolling road with dashed lane markings
  • Spawns & manages obstacle vehicles, pedestrians, traffic lights
  • Exposes a render() method that returns the raw RGB frame
"""

import random
import math
import pygame
import numpy as np
import config as C
import os

def _generate_noise_surface(width, height, base_color, noise_variation=15, grain_scale=1):
    small_w = max(1, int(width // grain_scale))
    small_h = max(1, int(height // grain_scale))
    
    noise = np.random.normal(0, noise_variation, (small_w, small_h, 3))
    base = np.array(base_color, dtype=float)
    img = base + noise
    img = np.clip(img, 0, 255).astype(np.uint8)
    
    surf = pygame.surfarray.make_surface(img)
    if grain_scale > 1:
        surf = pygame.transform.scale(surf, (width, height))
    return surf

def _create_tree_sprite():
    sz = 50
    surf = pygame.Surface((sz, sz), pygame.SRCALPHA)
    # Shadow
    pygame.draw.circle(surf, (0, 0, 0, 50), (sz//2 + 5, sz//2 + 5), 18)
    # Base
    pygame.draw.circle(surf, (20, 70, 25), (sz//2, sz//2), 20)
    # Mid
    pygame.draw.circle(surf, (30, 100, 30), (sz//2 - 3, sz//2 - 3), 15)
    # Top highlight
    pygame.draw.circle(surf, (45, 130, 40), (sz//2 - 6, sz//2 - 6), 9)
    return surf

class Obstacle:

    def __init__(self, screen_height, obs_type, assets):
        self.obs_type = obs_type
        self.assets = assets
        self.active_image = None
        self.state = 'red' if obs_type == 'traffic_light' else None
        
        if obs_type == 'car':
            self.w, self.h = C.OBSTACLE_WIDTH, C.OBSTACLE_HEIGHT
            lane_idx = random.randint(0, C.LANES - 1)
            self.logical_x = C.ROAD_LEFT + lane_idx * C.LANE_WIDTH + C.LANE_WIDTH // 2 - self.w // 2 + random.randint(-15, 15)
            self.x = self.logical_x
            self.y = -self.h
            self.speed_y = random.uniform(C.OBSTACLE_SPEED_MIN, C.OBSTACLE_SPEED_MAX)
            self.target_speed = self.speed_y
            self.logical_speed_x = 0
            self.active_image = assets['car']
            
            # 30% chance this car will aggressively cut into an adjacent lane
            self.is_cut_off_car = random.random() < 0.3
            if C.LANES > 1:
                if lane_idx == 0:
                    self.target_lane_idx = 1
                elif lane_idx == C.LANES - 1:
                    self.target_lane_idx = C.LANES - 2
                else:
                    self.target_lane_idx = lane_idx + random.choice([-1, 1])
            else:
                self.target_lane_idx = 0
            
        elif obs_type == 'pedestrian':
            self.w, self.h = 30, 30
            # Start off the road
            side = random.choice([-1, 1])
            if side == -1:
                self.logical_x = C.ROAD_LEFT - 40
                self.logical_speed_x = 2
            else:
                self.logical_x = C.ROAD_RIGHT + 10
                self.logical_speed_x = -2
            self.x = self.logical_x
            self.y = -self.h
            self.speed_y = 0  # Only moves down with the road
            self.active_image = assets['pedestrian']
            
        elif obs_type == 'traffic_light':
            self.w, self.h = 20, 60
            self.logical_x = C.ROAD_RIGHT + 5
            self.x = self.logical_x
            self.y = -self.h
            self.speed_y = 0 
            self.logical_speed_x = 0
            self.timer = 0
            self.active_image = assets['traffic_light_red']
            
        self.rect = pygame.Rect(int(self.x), int(self.y), self.w, self.h)

    def update(self, road_speed, all_obstacles, env_ref):
        # Intelligent Driver Model (IDM) for obstacle cars to brake for traffic
        if self.obs_type == 'car':
            closest_dist = float('inf')
            for other in all_obstacles:
                if other is not self and other.y > self.y and abs(getattr(other, 'logical_x', other.x) - self.logical_x) < 30: # Ahead in same lane
                    dist = other.y - (self.y + self.h)
                    if dist > 0 and dist < closest_dist:
                        closest_dist = dist
            
            # Braking & Accel logic
            if closest_dist < 60:
                self.speed_y -= 0.15 # Brake
            elif hasattr(self, 'target_speed') and self.speed_y < self.target_speed:
                self.speed_y += 0.05 # Accelerate

            # Cut-off logic: drift into target lane
            if getattr(self, 'is_cut_off_car', False):
                if 50 < self.y < C.SCREEN_HEIGHT / 1.5:
                    target_x = C.ROAD_LEFT + self.target_lane_idx * C.LANE_WIDTH + C.LANE_WIDTH // 2 - self.w // 2
                    if self.logical_x < target_x - 10:
                        self.logical_speed_x = 1.0  # Drift right
                    elif self.logical_x > target_x + 10:
                        self.logical_speed_x = -1.0 # Drift left
                    else:
                        self.logical_speed_x = 0
                        self.is_cut_off_car = False # Reached center
                
            self.speed_y = max(C.OBSTACLE_SPEED_MIN - 1, min(C.OBSTACLE_SPEED_MAX, self.speed_y))

        self.y += road_speed + self.speed_y
        self.logical_x += self.logical_speed_x
        
        # Apply the track rotation physically to the object
        self.x = self.logical_x + env_ref.get_curve_offset(self.y)
        
        if self.obs_type == 'traffic_light':
            self.timer += 1
            # Cycle every 200 frames
            if self.timer % 200 == 0:
                self.state = 'green' if self.state == 'red' else 'red'
                self.active_image = self.assets[f'traffic_light_{self.state}']

        self.rect.topleft = (int(self.x), int(self.y))

    def draw(self, surface):
        if self.active_image:
            # Draw a simple drop shadow
            shadow_rect = self.rect.copy()
            shadow_rect.y += 10
            shadow_rect.x += 5
            shadow_surf = pygame.Surface((shadow_rect.width, shadow_rect.height), pygame.SRCALPHA)
            pygame.draw.ellipse(shadow_surf, (0, 0, 0, 80), shadow_surf.get_rect())
            surface.blit(shadow_surf, shadow_rect)
            
            surface.blit(self.active_image, self.rect)
        else:
            pygame.draw.rect(surface, (255, 0, 255), self.rect) # Fallback

    @property
    def off_screen(self):
        return self.y > C.SCREEN_HEIGHT + 50


class Environment:
    def __init__(self, surface: pygame.Surface):
        self.surface = surface
        self.w = C.SCREEN_WIDTH
        self.h = C.SCREEN_HEIGHT
        self.scroll_y = 0
        self.track_scroll = 0
        self.obstacles: list[Obstacle] = []
        self._spawn_timer = 0
        self.road_speed = C.CAR_MIN_SPD
        
        # Load assets once
        self.assets = {}
        target_sizes = {
            'car.png': (C.OBSTACLE_WIDTH, C.OBSTACLE_HEIGHT),
            'pedestrian.png': (30, 30),
            'traffic_light_red.png': (20, 60),
            'traffic_light_green.png': (20, 60)
        }
        for name, size in target_sizes.items():
            path = os.path.join('assets', name)
            key = name.split('.')[0]
            if os.path.exists(path):
                img = pygame.image.load(path).convert_alpha()
                self.assets[key] = pygame.transform.scale(img, size)
            else:
                surf = pygame.Surface(size)
                surf.fill((255, 0, 255))
                self.assets[key] = surf

        # Generate Procedural Background Textures
        tex_h = self.h * 2
        
        # Single seamless fullscreen grass texture
        self.grass_tex = _generate_noise_surface(self.w, tex_h, C.COL_GRASS, noise_variation=20, grain_scale=3)
        tree_sprite = _create_tree_sprite()
        self._add_trees(self.grass_tex, tree_sprite)

    def _add_road_details(self, surface):
        w, h = surface.get_size()
        # Add tire marks / oil spills
        for _ in range(int(h * 0.05)):
            x = random.randint(0, w)
            y = random.randint(0, h)
            pw, ph = random.randint(10, 50), random.randint(40, 150)
            patch = pygame.Surface((pw, ph), pygame.SRCALPHA)
            pygame.draw.ellipse(patch, (20, 20, 25, 30), (0, 0, pw, ph)) # Subtle dark patch
            surface.blit(patch, (x, y))

    def _add_trees(self, surface, sprite):
        w, h = surface.get_size()
        density = 0.00015
        num_trees = int(w * h * density)
        for _ in range(num_trees):
            x = random.randint(-15, w - 10)
            y = random.randint(0, h)
            surface.blit(sprite, (x, y))

    def get_curve_offset(self, screen_y):
        return 0

    def update(self, road_speed: float):
        self.road_speed = road_speed
        self.scroll_y = (self.scroll_y + road_speed) % (self.h * 2)
        self.track_scroll += road_speed

        self._spawn_timer += 1
        if self._spawn_timer >= C.OBSTACLE_SPAWN_INTERVAL:
            self._spawn_timer = 0
            ptype = random.choices(['car', 'pedestrian', 'traffic_light'], weights=[60, 20, 20])[0]
            self.obstacles.append(Obstacle(self.h, ptype, self.assets))

        for obs in self.obstacles:
            obs.update(road_speed, self.obstacles, self)

        self.obstacles = [o for o in self.obstacles if not o.off_screen]

    def draw(self):
        self._draw_background()
        self._draw_road()
        self._draw_lane_markings()
        for obs in self.obstacles:
            obs.draw(self.surface)
        return self.surface

    def get_frame(self) -> np.ndarray:
        raw = pygame.surfarray.array3d(self.surface)
        return raw.transpose((1, 0, 2))

    def get_obstacles(self) -> list[Obstacle]:
        return self.obstacles

    def _draw_background(self):
        offset = int(self.scroll_y)
        h2 = self.h * 2
        y1 = offset % h2
        y2 = (offset % h2) - h2

        self.surface.blit(self.grass_tex, (0, y1))
        self.surface.blit(self.grass_tex, (0, y2))

    def _draw_road(self):
        segments = 40
        h_step = self.h / segments
        pts_left, pts_right = [], []
        
        for i in range(segments + 1):
            y = i * h_step
            offset_x = self.get_curve_offset(y)
            pts_left.append((C.ROAD_LEFT + offset_x, y))
            pts_right.append((C.ROAD_RIGHT + offset_x, y))
            
        # Compile seamless road snaking polygon
        road_poly = pts_left + list(reversed(pts_right))
        pygame.draw.polygon(self.surface, C.COL_ROAD, road_poly)
        
        pygame.draw.lines(self.surface, C.COL_CURB, False, pts_left, 8)
        pygame.draw.lines(self.surface, C.COL_CURB, False, pts_right, 8)

        # Draw outer yellow boundary lines over the curbs
        pygame.draw.lines(self.surface, (255, 220, 0), False, pts_left, 3)
        pygame.draw.lines(self.surface, (255, 220, 0), False, pts_right, 3)

    def _draw_lane_markings(self):
        segments = 30
        h_step = self.h / segments
        dash_h, dash_gap = 40, 40
        step = dash_h + dash_gap
        
        for lane in range(1, C.LANES):
            logical_x = C.ROAD_LEFT + lane * C.LANE_WIDTH
            
            for i in range(segments):
                y1 = i * h_step
                y2 = (i + 1) * h_step
                track_y = self.scroll_y - y1
                
                if int(track_y) % step < dash_h:
                    x1 = logical_x + self.get_curve_offset(y1)
                    x2 = logical_x + self.get_curve_offset(y2)
                    pygame.draw.line(self.surface, C.COL_LANE_MARK, (x1, y1), (x2, y2), 4)
