# EcoTwin: Smart Waste Management Digital Twin

### AI-assisted waste segregation, bin telemetry, and collection planning

<p>
   <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white" alt="Python 3.10+" />
   <img src="https://img.shields.io/badge/UI-Streamlit-FF4B4B?logo=streamlit&logoColor=white" alt="Streamlit" />
   <img src="https://img.shields.io/badge/Vision-Ultralytics%20YOLOv8-111F68" alt="Ultralytics YOLOv8" />
   <img src="https://img.shields.io/badge/Sprint-48%20hours-16A085" alt="48-hour hackathon sprint" />
   <img src="https://img.shields.io/badge/Status-Hackathon%20MVP-orange" alt="Hackathon MVP" />
</p>

**EcoTwin** is an AI-integrated prototype built during a 48-hour sprint for **Problem Track 1**. It combines a waste-segregation station with a digital twin of a smart-bin network, estimated sensor telemetry, and route-priority recommendations.

> **MVP status:** The dashboard, simulated/manual telemetry, login gate, and model-training workflows are implemented. Physical sensors are not connected, waste-specific checkpoints must be trained and installed separately, and Google GenAI route generation is not yet wired into the app. The current route planner is deterministic.

**Problem Track 1 · 48-hour hackathon build**

---

## 📄 Executive Summary & Core Objective

Waste streams are difficult to manage when items are mis-sorted, bin capacity is invisible, and collection routes are planned without current conditions. These problems matter in 2026 as cities face growing pressure to improve material recovery, reduce landfill use, and make waste operations more measurable.

EcoTwin's objective is to connect the **item-level view** of computer vision with the **network-level view** of a digital twin:

- Detect a waste item at an intake station using a camera or uploaded image.
- Suggest a segregation stream and record the virtual sorting action.
- Estimate each smart bin's fill from its dimensions and ultrasonic air-gap reading.
- Show bin status, map positions, sensor values, and collection priorities in one dashboard.

The current volume estimate assumes a rectangular bin and a reasonably level waste surface. The telemetry is simulated or entered manually until physical hardware is connected. EcoTwin is a decision-support prototype, not an autonomous waste-handling system.

## 🏗️ High-Level System Architecture

```text
                    +----------------------------------+
                    | PHYSICAL / SIMULATED BIN NETWORK |
                    +----------------+-----------------+
                                     |
                +--------------------+--------------------+
                |                                         |
                v                                         v
      +------------------------+             +------------------------+
      | SENSOR TELEMETRY       |             | CAMERA / IMAGE INPUT   |
      | Ultrasonic air gap     |             | Intake camera or       |
      | Temperature, battery   |             | uploaded photo         |
      +-----------+------------+             +-----------+------------+
                  |                                          |
                  v                                          v
      +------------------------+             +------------------------+
      | VOLUME ESTIMATOR       |             | YOLOv8 DETECTORS       |
      | Bin dimensions + gap   |             | General model          |
      | Liters + fill percent  |             | Optional e-waste model |
      +-----------+------------+             +-----------+------------+
                  |                                          |
                  |                              class + confidence
                  |                                          v
                  |                              +------------------------+
                  |                              | WASTE-STREAM MAPPER    |
                  |                              | Virtual bin + sort log |
                  |                              +-----------+------------+
                  |                                          |
                  +--------------------+--------------------+
                                       v
                    +----------------------------------+
                    | STREAMLIT DIGITAL TWIN          |
                    | Overview · Map · Sensors        |
                    | Analytics · Waste Segregation   |
                    +----------------+-----------------+
                                     v
                    +----------------------------------+
                    | ROUTE RECOMMENDATION            |
                    | Current: deterministic ranking  |
                    +----------------+-----------------+
                                     :
                                     : planned integration
                                     v
                    +----------------------------------+
                    | GOOGLE GENAI ROUTE EXPLANATION  |
                    | Planned; not called by the app   |
                    +----------------------------------+
```

**Current route output:** bins are ranked using their current fill readings. The `google-genai` dependency is present, but a GenAI routing service is not implemented yet.

## ⚙️ Supporting Objectives & Features

### Real-time Computer Vision Sorting

- Capture from the Intake Camera or upload a waste image.
- Run Ultralytics YOLOv8 object detection and map supported labels to virtual streams.
- Use a separate e-waste checkpoint when `models/ewaste_yolov8n.pt` is installed.
- Record virtual sorting actions and show per-stream capacity indicators.
- Keep a clearly identified generic COCO fallback when waste-specific weights are unavailable.

**Important:** YOLO identifies supported objects; it does not physically sort waste. The segregation-bin counts are prototype counters, not measured bin volume or verified contents. Review hazardous classifications before disposal.

### Live Telemetry Tracking / GIS Mapping

- Estimate fill height from ultrasonic sensor-to-waste distance.
- Estimate volume for rectangular bins using their internal dimensions.
- Show fill, estimated liters, air gap, temperature, battery, status, and location.
- Inspect readings, enter a manual ultrasonic measurement, view fill history, and see bins on a map.

The current readings are simulated or manually entered. No Raspberry Pi, ultrasonic sensor, load cell, or live GIS feed is connected yet.

### GenAI Route Optimization

- **Implemented now:** deterministic collection ordering based on bin fill.
- **Planned:** send selected, non-sensitive twin state to Google GenAI for an explainable route proposal, then validate the response against bin capacity, route constraints, and operating rules before showing it.

Do not treat generated recommendations as dispatch commands until the integration includes validation and operator approval.

## 🛠️ Tech Stack & Dependencies

| Technology | Role in EcoTwin | Status |
| :--- | :--- | :--- |
| Python | Application logic, data models, authentication, and training scripts | Implemented |
| Ultralytics YOLOv8 | Object detection and waste-model fine-tuning | Generic fallback included; dedicated waste weights are optional |
| Streamlit | Dashboard, login gate, intake workflow, sensors, analytics, and map | Implemented |
| Pandas | Telemetry tables and chart-ready data | Implemented |
| OpenCV | Camera capture, image decoding, and annotation | Implemented |
| SQLite | Local user accounts and failed-login records | Implemented |
| Google GenAI API (`google-genai`) | Intended route explanation and optimization | Dependency present; integration pending |
| Roboflow SDK | Optional e-waste dataset export for training | Training-only dependency |

## 💻 Project Structure

```text
ecotwin/
├── app.py                          # Streamlit entry point and page routing
├── core/
│   ├── auth.py                     # Accounts, password hashing, login throttling
│   ├── genai.py                    # Reserved for planned GenAI integration
│   ├── twin.py                     # Bin state, volume estimates, simulated telemetry
│   ├── vision.py                   # YOLOv8 inference and optional e-waste ensemble
│   └── waste_taxonomy.py           # Waste-stream mappings and model paths
├── ui/
│   ├── analytics.py                # Volume and fill trends
│   ├── authentication.py           # Login and first-admin setup screen
│   ├── bin_network.py              # Filterable bin operations and service controls
│   ├── camera.py                   # Intake camera preview
│   ├── navigation.py               # Sidebar and sign-out
│   └── sensors.py                  # Sensor table and manual ultrasonic input
├── scripts/
│   ├── prepare_taco.py              # COCO-to-YOLO dataset preparation
│   ├── train_waste_model.py         # General waste-stream training
│   └── train_ewaste_model.py        # Separate Roboflow e-waste training
├── datasets/
│   └── README.md                   # Dataset sources, setup, and training commands
├── models/                         # Generated checkpoints; not committed
├── runs/                           # Ultralytics output; not committed
├── data/                           # Local auth database; not committed
├── .env                            # Local secrets/configuration; never commit
├── .gitignore
├── requirements.txt
├── requirements-ewaste.txt        # Optional training dependencies
└── yolov8n.pt                      # Generic YOLOv8 starting weights
```

Dataset downloads, trained weights, training runs, the SQLite database, and local secrets should stay out of version control.

## 🚀 Installation & Setup

### 1. Clone the repository

The repository URL depends on your Git hosting account. This command prompts for the actual remote instead of assuming a URL:

```bash
read -r -p "Repository clone URL: " REPO_URL
git clone "$REPO_URL" ecotwin
cd ecotwin
```

In Windows PowerShell:

```powershell
$RepoUrl = Read-Host "Repository clone URL"
git clone $RepoUrl ecotwin
Set-Location ecotwin
```

### 2. Create and activate a virtual environment

macOS / Linux / Git Bash:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, allow it for this terminal session only:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
```

### 3. Install the application dependencies

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

For e-waste training only, stop running Streamlit/Python processes first, then install the optional dependencies. On Windows, a running process may lock OpenCV's native DLL during package replacement:

```bash
python -m pip install -r requirements-ewaste.txt
```

### 4. Configure local environment variables

Create `.env` locally; do not commit it.

macOS / Linux / Git Bash:

```bash
touch .env
```

Windows PowerShell:

```powershell
New-Item -ItemType File -Path .env -Force
```

Open `.env` in your editor and add only the settings you need:

```dotenv
ECOTWIN_AUTH_DB=data/auth.sqlite3
ROBOFLOW_API_KEY=
ROBOFLOW_EWASTE_WORKSPACE=computer-vision-learning-touhj
ROBOFLOW_EWASTE_PROJECT=capstone-kanon-2
ROBOFLOW_EWASTE_VERSION=4
EWASTE_MODEL_PATH=models/ewaste_yolov8n.pt
GOOGLE_API_KEY=
```

`ROBOFLOW_API_KEY` is required only to download the e-waste training dataset. `GOOGLE_API_KEY` is reserved for the planned GenAI work and is not currently consumed by the app. Keep real keys in your local `.env` file and never commit that file.

### 5. Create the first administrator

Run once from the project root. The password is entered through a hidden terminal prompt and stored as a salted hash in SQLite:

```bash
python -m core.auth create-admin
```

### 6. Start EcoTwin

```bash
streamlit run app.py
```

Open the local URL printed by Streamlit and sign in with the administrator account. The app has no public self-registration. Local operator account management and role-based authorization are not yet implemented.

## 🎓 Model Training

For the general waste model, prepare TACO and train only after reviewing the generated class counts:

```bash
python -m scripts.prepare_taco --download-images
python -m scripts.train_waste_model --data datasets/processed/taco_yolo/dataset.yaml
```

For the separate e-waste stream, configure `ROBOFLOW_API_KEY` in `.env`, install `requirements-ewaste.txt`, then run:

```bash
python -m scripts.train_ewaste_model --epochs 60 --batch 8
```

Training requires internet access and may take a long time on CPU-only hardware. The e-waste script validates mAP50 before installing its checkpoint. See [datasets/README.md](datasets/README.md) for dataset coverage, licensing, and limitations. No trained waste-specific weights are bundled by default.

## 🔮 Future Roadmap

- **Edge sensing:** connect Raspberry Pi or similar gateways to ultrasonic level sensors, load cells, temperature sensors, and camera stations over MQTT.
- **Persistent twin history:** replace in-memory telemetry with a time-series store and expose sensor health/last-seen state.
- **Validated GenAI routing:** connect Google GenAI to an explainable route planner with constraints, operator approval, and a deterministic fallback.
- **Production access control:** add admin-managed operator accounts, role enforcement, audit logs, and secure deployment secrets.
- **City-wide deployment:** move ingestion and storage to a cloud service, add tenant/site boundaries, monitoring, backups, and managed model releases.
- **Model quality:** gather locally representative waste images, address class imbalance, test contamination cases, and track per-class precision/recall before autonomous use.