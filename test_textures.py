import pygame
import numpy as np

def generate_noise_surface(width, height, base_color, noise_variation=15, grain_scale=1):
    small_w = max(1, width // grain_scale)
    small_h = max(1, height // grain_scale)
    
    noise = np.random.normal(0, noise_variation, (small_w, small_h, 3))
    base = np.array(base_color, dtype=float)
    img = base + noise
    img = np.clip(img, 0, 255).astype(np.uint8)
    
    surf = pygame.surfarray.make_surface(img)
    if grain_scale > 1:
        surf = pygame.transform.scale(surf, (width, height))
    return surf

pygame.init()
s1 = generate_noise_surface(300, 700, (45, 45, 50), 10, grain_scale=1)
s2 = generate_noise_surface(200, 700, (90, 160, 60), 12, grain_scale=3)
print(s1.get_size(), s2.get_size())
