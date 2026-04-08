# ─────────────────────────────────────────────
#  config.py  –  Global project configuration
# ─────────────────────────────────────────────

# Window
SCREEN_WIDTH  = 900
SCREEN_HEIGHT = 700
FPS           = 60
TITLE         = "Autonomous Car Simulator"

# Road geometry
ROAD_LEFT   = 200          # left edge of the road (px)
ROAD_RIGHT  = 700          # right edge of the road
LANES       = 2            # Number of lanes
LANE_WIDTH  = (ROAD_RIGHT - ROAD_LEFT) // LANES
LANE_CENTER = (ROAD_LEFT + ROAD_RIGHT) // 2 # Spawn explicitly in the center of the road

# Car
CAR_WIDTH    = 40
CAR_HEIGHT   = 70
CAR_MAX_SPD  = 6           # pixels / frame
CAR_MIN_SPD  = 2
CAR_ACCEL    = 0.1
CAR_DECEL    = 0.3         # braking force
STEERING_SPD = 3           # degrees / frame
MAX_STEER    = 30          # max steering angle (degrees)

# Obstacle spawning
OBSTACLE_SPAWN_INTERVAL = 120   # frames between spawns
OBSTACLE_WIDTH          = 40
OBSTACLE_HEIGHT         = 70
OBSTACLE_SPEED_MIN      = 2
OBSTACLE_SPEED_MAX      = 5
WARNING_DISTANCE        = 200   # pixels – yellow alert
DANGER_DISTANCE         = 100   # pixels – red brake

# Lane detection (CV)
ROI_TOP_RATIO    = 0.55        # top of region‑of‑interest (fraction of height)
HOUGH_THRESHOLD  = 30
HOUGH_MIN_LENGTH = 50
HOUGH_MAX_GAP    = 100

# Colours  (R, G, B)
COL_SKY        = (135, 206, 235)
COL_ROAD       = ( 45,  45,  50)
COL_LANE_MARK  = (255, 255, 255)
COL_CURB       = (180, 180, 190)
COL_GRASS      = ( 90, 160,  60)
COL_CAR        = ( 30, 144, 255)
COL_OBSTACLE   = (220,  50,  50)
COL_HUD_BG     = (  0,   0,   0, 160)   # used with surface alpha
COL_GREEN      = ( 50, 220,  80)
COL_YELLOW     = (255, 200,   0)
COL_RED        = (220,  50,  50)
COL_WHITE      = (255, 255, 255)
COL_DARK       = ( 20,  20,  25)
COL_ACCENT     = ( 30, 144, 255)
