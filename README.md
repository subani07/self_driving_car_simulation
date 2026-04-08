# Autonomous Car Simulation

A robust autonomous driving simulation project built in Python. This project features high-fidelity procedural simulation, incorporating sensor fusion (combining computer vision and simulated LIDAR), and a PID controller for stable steering, lane-keeping, and obstacle evasion.

## Features
- **Sensor Fusion**: Integrates computer vision with LIDAR-based distance measurements for accurate forward obstacle detection.
- **PID Controller**: Ensures smooth and stable steering, lane-keeping, and trajectory tracking.
- **Procedural Environment**: Dynamic, multi-lane traffic environments for testing control logic.
- **Real-time Telemetry Dashboard (HUD)**: Displays real-time metrics of the perception and control systems.

## Installation

1. Clone this repository (or copy the project files to a local directory).
2. Create a virtual environment:
   ```bash
   python -m venv .venv
   ```
3. Activate the virtual environment:
   - On Windows: `.venv\Scripts\activate`
   - On macOS/Linux: `source .venv/bin/activate`
4. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Simulation

Execute the main script to start the simulation:
```bash
python main.py
```