"""
main.py
───────
Entry point for the Autonomous Car Simulator.

Ties together:
  - Pygame environment & rendering
  - OpenCV perception pipeline
  - Autonomous controller
  - Heads-Up Display
"""

import sys
import pygame
import cv2


import config as C
from environment import Environment
from car import Car
from perception import Perception
from controller import Controller
from hud import HUD


def main():
    # ── 1. Init Pygame ──────────────────────────
    pygame.init()
    screen = pygame.display.set_mode((C.SCREEN_WIDTH, C.SCREEN_HEIGHT))
    pygame.display.set_caption(C.TITLE)
    clock = pygame.time.Clock()

    # ── 2. Init modules ─────────────────────────
    # The environment draws onto 'env_surface' which we later blit to screen.
    env_surface = pygame.Surface((C.SCREEN_WIDTH, C.SCREEN_HEIGHT))
    env = Environment(env_surface)
    
    car = Car()
    perception = Perception()
    controller = Controller()
    hud = HUD()

    print("\n🏁 Autonomous Car Simulation Started 🏁")
    print("Press ESC or close the window to quit.\n")

    running = True
    while running:
        # ── Events ──────────────────────────────
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

        # ── World Update ────────────────────────
        # Step the environment (scrolling road, obstacles)
        env.update(car.speed)
        
        # Render environment safely onto env_surface
        raw_env_surf = env.draw()

        # ── Perception Pipeline ─────────────────,
        # Extract the raw RGB array from the drawn environment
        rgb_frame = env.get_frame()
        
        # Pass to OpenCV to detect lanes & compute offset
        perception_data = perception.process(rgb_frame, car.x)

        # ── Decision & Control ──────────────────
        # Controller decides steering and speed using OpenCV object detections
        # fused with accurate simulated LIDAR distances
        controller.decide(car, perception_data, env.get_obstacles())
        
        # Car executes the physics
        car.update()

        # ── Final Rendering (Pygame screen) ─────
        # Blit the environment
        screen.blit(raw_env_surf, (0, 0))
        
        # Draw the car
        car.draw(screen)

        # Draw the HUD
        hud.draw(screen, car, controller.get_status(),
                 perception_data, clock.get_fps())

        pygame.display.flip()

        # ── Debug Window (OpenCV) ───────────────
        cv2.imshow("CV Perception Debug", perception_data["debug_frame"])
        if cv2.waitKey(1) & 0xFF == 27:  # ESC in cv2 window
            running = False

        # ── Tick ────────────────────────────────
        clock.tick(C.FPS)

    # ── Cleanup ─────────────────────────────────
    pygame.quit()
    cv2.destroyAllWindows()
    sys.exit()

if __name__ == "__main__":
    main()
