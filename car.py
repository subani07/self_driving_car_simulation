"""
car.py
──────
Player / autonomous car model.
Handles position, steering, speed, and drawing.
"""

import math
import pygame
import config as C


class Car:
    def __init__(self):
        # Start at bottom-centre of road
        self.x = float(C.LANE_CENTER)
        self.y = float(C.SCREEN_HEIGHT - 120)
        self.speed     = float(C.CAR_MIN_SPD)
        self.heading   = 0.0        # radians; 0 = straight up
        self.steer     = 0.0        # steering wheel angle (degrees)
        self.wheelbase = 40.0       # distance between axles
        self.braking   = False

        # Build car sprite (drawn once, rotated as needed)
        self._sprite = self._build_sprite()
        self.rect = pygame.Rect(
            self.x - C.CAR_WIDTH // 2,
            self.y - C.CAR_HEIGHT // 2,
            C.CAR_WIDTH,
            C.CAR_HEIGHT,
        )

    # ── Physics ────────────────────────────────

    def apply_steer(self, delta: float):
        """delta > 0 → right, delta < 0 → left."""
        self.steer = max(-C.MAX_STEER,
                    min( C.MAX_STEER, self.steer + delta))

    def set_steer_direct(self, target_steer: float):
        """Controller can set steer angle directly."""
        self.steer = max(-C.MAX_STEER,
                    min( C.MAX_STEER, target_steer))

    def accelerate(self):
        self.speed = min(C.CAR_MAX_SPD, max(C.CAR_MIN_SPD, self.speed + C.CAR_ACCEL))
        self.braking = False

    def brake(self):
        self.speed = max(0.0, self.speed - C.CAR_DECEL)
        self.braking = True

    def update(self):
        """Move the car based on current steer (stable physics)."""
        # Convert steer angle to lateral movement directly to avoid oscillation
        steer_rad = math.radians(self.steer)
        
        # Enforce a baseline effective speed for lateral physics so we can still dodge when fully braked
        effective_speed = max(self.speed, 3.0)
        dx = math.sin(steer_rad) * effective_speed
        self.x += dx
        
        # For realistic visuals, gracefully tilt the car's body to match the steering direction
        target_heading = math.radians(self.steer * 0.8)
        self.heading += (target_heading - self.heading) * 0.15

        # Clamp loosely to screen bounds since road curves dynamically
        half_w = C.CAR_WIDTH // 2
        self.x = max(half_w + 10, min(C.SCREEN_WIDTH - half_w - 10, self.x))

        self.rect.center = (int(self.x), int(self.y))

    # ── Drawing ────────────────────────────────

    def draw(self, surface: pygame.Surface):
        vis_angle = math.degrees(self.heading)

        # Draw a rotated drop shadow
        shadow = pygame.Surface((C.CAR_WIDTH, C.CAR_HEIGHT), pygame.SRCALPHA)
        pygame.draw.rect(shadow, (0, 0, 0, 80), (0, 0, C.CAR_WIDTH, C.CAR_HEIGHT), border_radius=8)
        rotated_shadow = pygame.transform.rotate(shadow, -vis_angle)
        shad_rect = rotated_shadow.get_rect(center=(int(self.x + 6), int(self.y + 10)))
        surface.blit(rotated_shadow, shad_rect)

        rotated  = pygame.transform.rotate(self._sprite, -vis_angle)
        blit_rect = rotated.get_rect(center=(int(self.x), int(self.y)))
        surface.blit(rotated, blit_rect)

        # Brake lights
        if self.braking:
            bl = pygame.Rect(self.rect.x + 3,
                             self.rect.bottom - 14, 12, 8)
            br = pygame.Rect(self.rect.right - 15,
                             self.rect.bottom - 14, 12, 8)
            pygame.draw.rect(surface, (255, 60, 60), bl, border_radius=2)
            pygame.draw.rect(surface, (255, 60, 60), br, border_radius=2)

    # ── Collision ──────────────────────────────

    def collides_with(self, obstacle) -> bool:
        return self.rect.colliderect(obstacle.rect)

    def distance_to(self, obstacle) -> float:
        return max(0.0, obstacle.rect.top - self.rect.top)

    # ── Private ────────────────────────────────

    @staticmethod
    def _build_sprite() -> pygame.Surface:
        w, h = C.CAR_WIDTH, C.CAR_HEIGHT
        surf = pygame.Surface((w, h), pygame.SRCALPHA)

        # Body
        body_colour = C.COL_CAR
        pygame.draw.rect(surf, body_colour,
                         (0, 0, w, h), border_radius=8)

        # Roof highlight
        pygame.draw.rect(surf, (60, 170, 255),
                         (4, 8, w - 8, h // 3), border_radius=5)

        # Windshield
        pygame.draw.rect(surf, (180, 225, 255),
                         (5, 10, w - 10, 20), border_radius=4)

        # Rear window
        pygame.draw.rect(surf, (180, 225, 255),
                         (5, h - 28, w - 10, 16), border_radius=3)

        # Headlights
        pygame.draw.ellipse(surf, (255, 250, 180),
                            (4, 4, 12, 8))
        pygame.draw.ellipse(surf, (255, 250, 180),
                            (w - 16, 4, 12, 8))

        # Wheels
        wc = (20, 20, 20)
        pygame.draw.rect(surf, wc, (-4, 12, 8, 18), border_radius=3)
        pygame.draw.rect(surf, wc, (w - 4, 12, 8, 18), border_radius=3)
        pygame.draw.rect(surf, wc, (-4, h - 30, 8, 18), border_radius=3)
        pygame.draw.rect(surf, wc, (w - 4, h - 30, 8, 18), border_radius=3)

        return surf
