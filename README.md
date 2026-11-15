# Agriculture Manipulation Robot (AgriBot OS)
### Autonomous Row Navigation, OpenCV Vision & 4-DOF Robotic Arm Mission Planner

An end-to-end, simulation-first full-stack robotic software platform engineered for autonomous agricultural navigation, real-time computer vision crop detection, 4-DOF kinematic arm harvesting manipulation, and cloud-accessible mission control teleoperation.

* **GitHub Repository:** [https://github.com/ShreyaCodes07/Agriculture_Manipulation_Robot](https://github.com/ShreyaCodes07/Agriculture_Manipulation_Robot)

---

## 🌟 Key System Capabilities

- **Single Page Application (SPA) Web Dashboard:** Interactive dashboard with dark/light mode, real-time telemetry meters, D-Pad chassis drive, and servo joint controls.
- **Autonomous Row Navigation & A\* Path Planner:** Waypoint calculation, obstacle avoidance (bypasses field rocks and boundaries), and target queue sequencing.
- **Computer Vision Pipeline (OpenCV):** Synthetic pinhole camera simulation, HSV color segmentation, bounding box localization, and 2D-to-world Cartesian projection.
- **4-DOF Robotic Manipulator Arm:** Analytical Inverse Kinematics (IK), Forward Kinematics (FK), mechanical limit clamping, and 8-step pick-and-place harvesting state machine.
- **Automated Verification Matrix:** 26 automated unit and integration tests covering physical kinematics, vision filters, and mission lifecycle.
- **Zero-Friction Cloud Deployment:** Pre-configured for 24/7 cloud hosting on Render, Railway, Docker, or instant public HTTPS tunneling.

---

## 🚀 Quick Start (Local Execution)

### Prerequisites
- Python 3.10+ (tested on Python 3.11, 3.12, 3.14)
- Web browser (Chrome, Edge, Firefox, Safari)

### 1. Run via Batch Script (Windows)
Double-click `start_local.bat` or run:
```powershell
.\start_local.bat
```

### 2. Run Manually via CLI
```bash
# Install dependencies
pip install -r requirements.txt

# Start backend server with unified frontend SPA serving
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```
Open your browser at **[http://localhost:8000](http://localhost:8000)**.

---

## 🌐 Instant Public HTTPS URL (Free & No Signup)

To share the application immediately with judges, professors, and teammates directly from your laptop:

1. Ensure the local server is running (`start_local.bat`).
2. Double-click `start_public_tunnel.bat` or run:
   ```bash
   ssh -R 80:127.0.0.1:8000 nokey@localhost.run
   ```
3. An encrypted public HTTPS URL (e.g., `https://<unique-id>.lhr.life`) will appear in your console.
4. Share this link — anyone on mobile or desktop can access the full live dashboard and simulation!

---

## ☁️ Permanent 24/7 Cloud Deployment (Render.com)

The project includes built-in `render.yaml`, `Procfile`, and `Dockerfile` configurations.

### Option A: Automatic Deploy with `render.yaml`
1. Push your repository to GitHub:
   ```bash
   git add .
   git commit -m "Configure production cloud deployment"
   git push origin main
   ```
2. Log into [Render.com](https://render.com).
3. Click **New +** > **Blueprint**.
4. Connect the GitHub repository `Agriculture_Manipulation_Robot`.
5. Render will automatically read `render.yaml` and provision the Web Service on the free tier.
6. Your live public production URL will be:
   `https://agri-manipulation-robot.onrender.com`

### Option B: Manual Web Service Setup
- **Environment:** Python
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `python -m uvicorn main:app --host 0.0.0.0 --port $PORT`
- **Environment Variables:**
  - `PYTHONPATH`: `backend`
  - `MODE`: `simulation`

---

## ⚙️ Environment Variables

| Variable | Default Value | Description |
|---|---|---|
| `PORT` | `8000` | Web server listening port |
| `HOST` | `0.0.0.0` | Network binding interface |
| `MODE` | `simulation` | Operation mode (`simulation` or `hardware`) |
| `DATABASE_URL` | `sqlite:///./agri_robot.db` | SQLAlchemy database connection string |
| `OBSTACLE_BRAKE_THRESHOLD_CM` | `30.0` | Emergency stop distance threshold |

---

## 🧪 Running Automated Tests

Run the full 26-test verification suite:
```bash
pytest backend/tests
```

All 26 test suites cover:
- `test_arm.py`: Forward kinematics, inverse kinematics, boundary clamping, gripper commands, and pick sequence.
- `test_mission.py`: A* path planning, rock collision avoidance, waypoint navigation, target queueing.
- `test_simulation.py`: Canvas world snapshot, differential chassis kinematics, SPA routing.
- `test_vision.py`: Camera frame generation, HSV color thresholding, bounding box localization.
