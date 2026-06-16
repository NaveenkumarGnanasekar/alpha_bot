# Alpha Bot 🤖

A custom differential-drive robot that autonomously navigates an indoor environment and responds to natural language commands — built entirely on ROS 2, Gazebo, Nav2, and a local LLM.

---
<img width="1266" height="882" alt="Screenshot from 2026-06-16 11-26-56" src="https://github.com/user-attachments/assets/4984f996-53d2-4a5a-8782-620ec9cf205d" />

## Demo

> Say `"go to workspaceA"` — the robot plans and drives there autonomously.
> Say `"remember this as room3"` — that spot is saved and immediately usable.

---
<img width="2005" height="1045" alt="Screenshot from 2026-06-16 15-01-21" src="https://github.com/user-attachments/assets/92013715-4d8c-4875-b43a-18219aa804b4" />
## Concepts Used

### 1. Robot Modeling (URDF / Xacro)
The ALPHA robot was designed from scratch using **URDF (Unified Robot Description Format)**. Xacro macros keep the description modular — separate files handle the chassis, wheels, LiDAR, camera, and ros2_control interface. Custom STL meshes define the visual appearance.

### 2. Simulation (Gazebo Harmonic)
The robot is simulated in **Gazebo Harmonic**, a physics-based simulator. A custom **5-room indoor world** was built in SDF — corridors, doorways, and rooms — designed to challenge the navigation stack with realistic indoor geometry.

### 3. ros2_control + Differential Drive
Wheel actuation is handled by **ros2_control** with the `diff_drive_controller` plugin. It subscribes to velocity commands and drives the left/right wheels accordingly, publishing odometry back to ROS 2.

> **Jazzy note:** `diff_drive_controller` in ROS 2 Jazzy requires `TwistStamped` while Nav2 publishes plain `Twist`. A `twist_stamper` node bridges the gap.


<img width="1928" height="1080" alt="Screenshot from 2026-06-16 11-37-48" src="https://github.com/user-attachments/assets/7b10b455-be3c-4649-9782-e61129048663" />

### 4. SLAM — Mapping
Before autonomous navigation, the robot needs a map. **SLAM (Simultaneous Localization and Mapping)** was used to drive the robot through the world manually while it built an occupancy grid map — a 2D image where white = free space, black = walls, grey = unknown. The result is saved as `first_map.pgm` + `first_map.yaml`.

### 5. AMCL — Localization
Once the map is saved, **AMCL (Adaptive Monte Carlo Localization)** takes over. It uses a **particle filter** — thousands of hypotheses about where the robot might be — and continuously narrows them down by comparing live LiDAR scans against the known map. The result is a real-time pose estimate (`/amcl_pose`) used by the entire navigation stack.

### 6. Nav2 — Autonomous Navigation
The **Nav2** stack handles getting from point A to point B:

<img width="1910" height="1045" alt="Screenshot from 2026-06-16 11-35-21" src="https://github.com/user-attachments/assets/c08d7920-79c3-4171-b812-d2da8c2566d9" />

| Component | Role |
|---|---|
| `map_server` | Serves the saved occupancy grid |
| `amcl` | Real-time localization on the map |
| `planner_server` (NavFn) | Computes a global path from current pose to goal |
| `controller_server` (MPPI) | Executes the path smoothly at the local level |
| `local_costmap` | Tracks nearby obstacles from LiDAR in real time |
| `global_costmap` | Inflates obstacles on the static map for safe planning |
| `bt_navigator` | Orchestrates all components via Behavior Trees |
| `collision_monitor` | Final safety layer — stops the robot if collision is imminent |
| `velocity_smoother` | Smooths velocity commands before they reach the wheels |

**MPPI (Model Predictive Path Integral)** was chosen over the default DWB controller for smoother trajectories through narrow doorways — it samples thousands of possible trajectories and picks the optimal one every cycle.

### 7. Twist Mux
**twist_mux** is a velocity multiplexer that merges multiple velocity sources (keyboard, joystick, Nav2) into a single `/cmd_vel` topic, using configurable priorities and timeouts.

### 8. Natural Language Commands (LLM)
The `alpha_bot_llm_nav` package adds a natural language interface on top of Nav2:

**Flow:**
```
[text / voice input]
        ↓
/user_command (ROS 2 topic)
        ↓
llm_commander node
  → loads waypoints.yaml (named poses)
  → builds system prompt with known locations
  → sends to Ollama (qwen2.5:1.5b) locally
  → receives structured JSON response
        ↓
Nav2 action goal (NavigateToPose / NavigateThroughPoses)
        ↓
Robot navigates
```

**Supported commands:**
```
"go to workspaceA"                      → navigate to a saved location
"visit Station A then Station B"        → multi-stop navigation
"remember this location as workspaceD"  → save current pose by name
"stop"                                  → cancel active goal
```

The LLM only decides **where** to go. Nav2 decides **how** to get there.

### 9. Waypoint Teaching
The `waypoint_teacher` node listens to `/amcl_pose`. When you publish a name to `/save_waypoint`, it records the robot's current `(x, y, yaw)` under that name in `waypoints.yaml`. The `llm_commander` reloads this file on every command — so newly taught locations are immediately usable without restarting anything.

### 10. Voice Input (faster-whisper)
The `voice_input` node provides push-to-talk speech recognition using **faster-whisper** — a local, offline speech-to-text model. Press Enter to start recording, press Enter again to transcribe and publish to `/user_command`. No cloud, no microphone streaming.

---

## Architecture

```
[text_input] / [voice_input]
          ↓
    /user_command
          ↓
   [llm_commander]  ←→  Ollama (qwen2.5:1.5b)
          ↓
   Nav2 Action Goal
          ↓
   [bt_navigator]
    ↙         ↘
[planner]   [controller]
    ↘         ↙
   [costmaps] ← /scan (LiDAR)
          ↓
   /cmd_vel (Twist)
          ↓
   [twist_stamper]
          ↓
   /cmd_vel (TwistStamped)
          ↓
   [diff_cont] → Gazebo
```

---
<img width="1910" height="1045" alt="Screenshot from 2026-06-16 11-29-21" src="https://github.com/user-attachments/assets/351e7426-15a9-4dec-bb3f-78d1e05325ff" />
## Tech Stack

| Layer | Technology |
|---|---|
| Simulation | Gazebo Harmonic |
| Robot middleware | ROS 2 Jazzy |
| Navigation | Nav2 (NavFn + MPPI + AMCL) |
| Robot control | ros2_control + diff_drive_controller |
| Local LLM | Ollama + qwen2.5:1.5b |
| Speech-to-text | faster-whisper (local) |
| Visualization | RViz2 |

---

## Quick Start

### Prerequisites
- ROS 2 Jazzy
- Gazebo Harmonic
- Ollama — `curl -fsSL https://ollama.com/install.sh | sh`
- Python deps — `pip install pyyaml requests faster-whisper sounddevice`

### Build
```bash
git clone https://github.com/<your-username>/alpha_bot.git
cd alpha_bot
colcon build
source install/setup.bash
```

### Pull LLM model
```bash
ollama pull qwen2.5:1.5b
```

### Launch
```bash
# Terminal 1 — simulation
ros2 launch alpha_bot sim_launch.launch.py

# Terminal 2 — localization
ros2 launch alpha_bot localization.launch.py

# Terminal 3 — navigation
ros2 launch alpha_bot navigation.launch.py

# Terminal 4 — LLM bridge
ros2 launch alpha_bot llm_nav.launch.py

# Terminal 5 — input
ros2 run alpha_bot text_input     # type commands
ros2 run alpha_bot voice_input    # or speak them
```

---

## What's Next

- VLM (Vision-Language Model) for camera-based scene understanding
- Map-free navigation — "go to the room with the open door"
- Real hardware deployment

---

https://github.com/user-attachments/assets/09c0aa18-ceba-4307-9dec-c3e61fc28555

## License

Apache 2.0
