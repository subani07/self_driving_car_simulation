"""
hud.py
──────
Heads‑Up Display overlay rendered on top of the Pygame window.
Shows: speed, steering angle, alert status, nearest obstacle distance,
lane offset, and a mini radar.
"""

import math
import pygame
import config as C


class HUD:
    """Draws all HUD elements onto a transparent overlay surface."""

    # Colours
    _BG      = (10, 12, 18)
    _PANEL   = (18, 22, 32)
    _BORDER  = (40, 50, 70)
    _GREEN   = (50, 220, 80)
    _YELLOW  = (255, 200, 0)
    _RED     = (220, 50, 50)
    _CYAN    = (0, 200, 220)
    _WHITE   = (230, 235, 245)
    _ORANGE  = (255, 140, 0)

    def __init__(self):
        pygame.font.init()
        try:
            self._font_lg = pygame.font.SysFont("Segoe UI", 22, bold=True)
            self._font_md = pygame.font.SysFont("Segoe UI", 16)
            self._font_sm = pygame.font.SysFont("Segoe UI", 13)
        except Exception:
            self._font_lg = pygame.font.Font(None, 26)
            self._font_md = pygame.font.Font(None, 20)
            self._font_sm = pygame.font.Font(None, 16)

    # ── Public ─────────────────────────────────

    def draw(self, surface: pygame.Surface,
             car, controller_status: dict,
             perception_data: dict, fps: float):
        """Render all HUD panels onto surface."""
        alert      = controller_status["alert"]
        nearest    = controller_status["nearest_dist"]
        lane_off   = perception_data.get("lane_offset", 0)
        steer      = car.steer
        speed_kmh  = car.speed * 10          # scale to look realistic

        # ── Left panel (telemetry) ─────────────
        self._draw_panel(surface, 8, 8, 190, 250)
        self._label(surface, "AUTONOMOUS CAR",  18, 16, self._CYAN,   self._font_md)
        self._label(surface, "─" * 22,           18, 34, self._BORDER, self._font_sm)

        self._stat(surface, "SPEED",   f"{speed_kmh:.0f} km/h",  18, 50,  self._GREEN)
        self._stat(surface, "PID OUT",   f"{steer:+.1f}°",          18, 76,  self._CYAN)
        self._stat(surface, "OFFSET",  f"{lane_off:+.0f} px",     18, 102, self._YELLOW)
        
        lidar_txt = "∞" if nearest == float("inf") else f"{nearest:.0f} px"
        self._stat(surface, "LIDAR", lidar_txt, 18, 128, self._WHITE)
        
        is_fused = controller_status.get("is_fused", False)
        fusion_txt = "STANDBY"
        if nearest != float("inf"):
            fusion_txt = "ACTIVE" if is_fused else "CV ONLY"
        fusion_col = self._GREEN if fusion_txt == "ACTIVE" else (self._YELLOW if fusion_txt == "CV ONLY" else self._BORDER)
        
        self._stat(surface, "FUSION", fusion_txt, 18, 154, fusion_col)

        # Alert badge
        acol, atxt = self._alert_style(alert)
        self._draw_badge(surface, atxt, acol, 18, 184, 174, 36)

        # FPS
        self._label(surface, f"FPS: {fps:.0f}", 18, 228, self._BORDER, self._font_sm)

        # ── Steering wheel indicator ───────────
        self._draw_steering_wheel(surface, steer)

        # ── Mini radar (top-right) ─────────────
        self._draw_radar(surface, nearest)

        # ── Screen-edge flash on DANGER / COLLISION ──
        if alert in ("DANGER", "COLLISION"):
            self._draw_alert_flash(surface, acol)

    # ── Private drawing helpers ────────────────

    @staticmethod
    def _draw_panel(surface, x, y, w, h, alpha=200):
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        s.fill((18, 22, 32, alpha))
        pygame.draw.rect(s, (40, 50, 70, 255), (0, 0, w, h), 1,
                         border_radius=8)
        surface.blit(s, (x, y))

    def _label(self, surface, text, x, y, colour, font):
        surf = font.render(text, True, colour)
        surface.blit(surf, (x, y))

    def _stat(self, surface, label, value, x, y, val_colour):
        self._label(surface, label, x, y, (120, 130, 150), self._font_sm)
        self._label(surface, value, x + 70, y, val_colour, self._font_md)

    @staticmethod
    def _alert_style(alert):
        mapping = {
            "SAFE"     : ((50, 220, 80),   "● SAFE"),
            "WARNING"  : ((255, 200, 0),   "▲ WARNING"),
            "DANGER"   : ((220, 50, 50),   "■ DANGER"),
            "COLLISION": ((255, 255, 255), "✕ COLLISION"),
        }
        return mapping.get(alert, ((150, 150, 150), alert))

    def _draw_badge(self, surface, text, colour, x, y, w, h):
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        r, g, b = colour
        s.fill((r, g, b, 50))
        pygame.draw.rect(s, colour + (220,), (0, 0, w, h), 2,
                         border_radius=6)
        surf = self._font_md.render(text, True, colour)
        tx = (w - surf.get_width())  // 2
        ty = (h - surf.get_height()) // 2
        s.blit(surf, (tx, ty))
        surface.blit(s, (x, y))

    def _draw_steering_wheel(self, surface, steer_angle):
        cx, cy, r = 95, C.SCREEN_HEIGHT - 90, 45
        self._draw_panel(surface, cx - r - 10, cy - r - 10,
                         (r + 10) * 2, (r + 10) * 2)
        # Outer ring
        pygame.draw.circle(surface, self._BORDER, (cx, cy), r, 3)
        # Spokes
        for spoke_a in (0, 120, 240):
            rad = math.radians(spoke_a + steer_angle * 2)
            ex  = cx + int(r * math.sin(rad))
            ey  = cy - int(r * math.cos(rad))
            pygame.draw.line(surface, self._CYAN, (cx, cy), (ex, ey), 2)
        # Centre dot
        pygame.draw.circle(surface, self._WHITE, (cx, cy), 6)
        # Label
        self._label(surface, f"{steer_angle:+.1f}°",
                    cx - 18, cy + r + 5, self._CYAN, self._font_sm)

    def _draw_radar(self, surface, nearest_dist):
        """Simple 1-D "proximity radar" on the top-right corner."""
        rx = C.SCREEN_WIDTH - 165
        ry = 8
        rw, rh = 158, 110
        self._draw_panel(surface, rx, ry, rw, rh)

        self._label(surface, "LIDAR FUSION RADAR", rx + 10, ry + 10,
                    self._CYAN, self._font_sm)

        # Bar chart
        bar_x = rx + 10
        bar_y = ry + 35
        bar_w = rw - 20
        bar_h = 20

        if nearest_dist == float("inf"):
            fill = 0
            bar_col = self._GREEN
        else:
            ratio   = max(0.0, 1.0 - nearest_dist / C.WARNING_DISTANCE)
            fill    = int(bar_w * ratio)
            if nearest_dist < C.DANGER_DISTANCE:
                bar_col = self._RED
            elif nearest_dist < C.WARNING_DISTANCE:
                bar_col = self._YELLOW
            else:
                bar_col = self._GREEN

        pygame.draw.rect(surface, self._BORDER,
                         (bar_x, bar_y, bar_w, bar_h), border_radius=4)
        if fill > 0:
            pygame.draw.rect(surface, bar_col,
                             (bar_x, bar_y, fill, bar_h), border_radius=4)

        dist_txt = "Path Clear" if nearest_dist == float("inf") \
                   else f"Target: {nearest_dist:.0f} px"
        self._label(surface, dist_txt, rx + 10, bar_y + 28,
                    self._WHITE, self._font_sm)

        # Threshold markers
        warn_x = bar_x + int(bar_w * (1 - C.WARNING_DISTANCE / C.WARNING_DISTANCE))
        dang_x = bar_x + int(bar_w * (1 - C.DANGER_DISTANCE  / C.WARNING_DISTANCE))
        pygame.draw.line(surface, self._YELLOW,
                         (bar_x + bar_w - int(bar_w * C.DANGER_DISTANCE  / C.WARNING_DISTANCE), bar_y),
                         (bar_x + bar_w - int(bar_w * C.DANGER_DISTANCE  / C.WARNING_DISTANCE), bar_y + bar_h), 1)

        # Dots representing nearby obstacles
        dot_y = ry + 82
        self._label(surface, "NEAR", rx + 10,  dot_y - 14, (100,110,130), self._font_sm)
        self._label(surface, "FAR",  rx + rw - 32, dot_y - 14, (100,110,130), self._font_sm)
        pygame.draw.line(surface, self._BORDER,
                         (rx + 10, dot_y), (rx + rw - 10, dot_y), 1)
        if nearest_dist != float("inf") and nearest_dist < C.WARNING_DISTANCE:
            dot_x = rx + 10 + int((rw - 20) * (1 - nearest_dist / C.WARNING_DISTANCE))
            pygame.draw.circle(surface, bar_col, (dot_x, dot_y), 6)

    @staticmethod
    def _draw_alert_flash(surface, colour):
        """Draw a coloured border flash when danger is detected."""
        s = pygame.Surface((C.SCREEN_WIDTH, C.SCREEN_HEIGHT), pygame.SRCALPHA)
        r, g, b = colour
        border = 6
        pygame.draw.rect(s, (r, g, b, 120),
                         (0, 0, C.SCREEN_WIDTH, C.SCREEN_HEIGHT),
                         border)
        surface.blit(s, (0, 0))
