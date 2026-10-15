# ♻️ EcoTwin: Smart Waste Management Digital Twin

> **AI-Powered Waste Segregation · IoT Bin Telemetry · Google Gemini Route Optimization**

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![Streamlit 1.40+](https://img.shields.io/badge/UI-Streamlit-FF4B4B?style=flat&logo=streamlit&logoColor=white)](https://streamlit.io)
[![YOLOv8](https://img.shields.io/badge/Vision-Ultralytics%20YOLOv8-111F68?style=flat)](https://github.com/ultralytics/ultralytics)
[![Google GenAI](https://img.shields.io/badge/Generative%20AI-Google%20Gemini-4285F4?style=flat&logo=google&logoColor=white)](https://aistudio.google.com)
[![Status](https://img.shields.io/badge/Status-Hackathon%20MVP-16A085?style=flat)](#)

---

## 📌 Overview

**EcoTwin** connects **computer vision at the intake bin** with an **IoT digital twin network** and **Google Gemini Generative AI** to solve urban waste management bottlenecks:

1. **Intelligent Waste Segregation:** Detects items via camera or image upload using YOLOv8, classifies them into **Compost**, **Recyclable**, **Hazardous**, or **Landfill**, and provides AI-generated eco-handling advice.
2. **Digital Twin of Smart Bins:** Monitors real-time ultrasonic fill levels, container volume (liters), temperature anomalies, battery health, and GIS coordinates across the city.
3. **GenAI Route Optimization:** Sends live network telemetry to **Google Gemini** (`gemini-2.5-flash`) to generate an explainable collection route, prioritizing overflow hazards and minimizing carbon emissions.
4. **EcoTwin AI Copilot:** A built-in assistant allowing municipal operators to ask operational questions in natural language (e.g. *"Which bins are at risk of overflow?"*).

---

## 🏗️ System Architecture

```text
               +-------------------------------------------+
               |        ECOTWIN DIGITAL TWIN PLATFORM      |
               +---------------------+---------------------+
                                     |
         +---------------------------+---------------------------+
         |                                                       |
         v                                                       v
+-------------------------------+               +-------------------------------+
|     VISION & INTAKE STATION   |               |    IOT TELEMETRY & SENSORS    |
| • Webcam or Image Upload      |               | • Ultrasonic sensor (fill %)  |
| • Ultralytics YOLOv8 Detector |               | • Temperature & battery stats |
| • Stream mapping (4 streams)  |               | • Digital twin geometry (cm/L)|
+---------------+---------------+               +---------------+---------------+
                |                                               |
                +-----------------------+-----------------------+
                                        |
                                        v
                    +---------------------------------------+
                    |        STREAMLIT DASHBOARD (UI)       |
                    | Overview · Segregation · GIS Map      |
                    | Sensors · Analytics · Settings        |
                    +-------------------+-------------------+
                                        |
                                        v
                    +---------------------------------------+
                    |       GOOGLE GEMINI GENERATIVE AI     |
                    |           (google-genai SDK)          |
                    | • Dynamic route collection plan       |
                    | • Material disposal & circular advice |
                    | • Natural-language operations copilot |
                    +---------------------------------------+
```

---

## 🛠️ Tech Stack

| Component | Technology | Description |
| :--- | :--- | :--- |
| **User Interface** | [Streamlit](https://streamlit.io/) | Interactive web dashboard with dark-mode aesthetics |
| **Object Detection** | [Ultralytics YOLOv8](https://docs.ultralytics.com/) | Real-time classification of waste items & e-waste |
| **Generative AI** | [Google GenAI SDK](https://ai.google.dev/) (`gemini-2.5-flash`) | Route reasoning, eco-disposal tips, and AI copilot |
| **Digital Twin Engine** | Python (`core/twin.py`) | Volume calculation from ultrasonic distance & geometry |
| **Computer Vision** | OpenCV & Pillow | Camera streaming, frame decoding, and annotation |
| **Data & Mapping** | Pandas & Plotly | Telemetry data tables, historical trends, and charts |
| **Authentication** | SQLite & PBKDF2 | Local admin authentication with salted password hashes |

---

## 📁 Project Structure

```text
CodeClash2.0_DSU/
├── app.py                      # Main Streamlit dashboard entry point
├── core/
│   ├── auth.py                 # User authentication & password hashing
│   ├── genai.py                # Google Gemini route planner, disposal advice & copilot
│   ├── twin.py                 # Smart bin digital twin, volume calculations & simulation
│   ├── vision.py               # YOLOv8 waste detection pipeline
│   └── waste_taxonomy.py       # Waste categories & stream mappings
├── ui/
│   ├── analytics.py            # Capacity charts and volume trends
│   ├── authentication.py       # Login portal
│   ├── bin_network.py          # Detailed bin grid and service controls
│   ├── camera.py               # Intake camera preview & capture
│   ├── navigation.py           # Sidebar & simulated deposit actions
│   ├── sensors.py              # Sensor telemetry & manual ultrasonic inputs
│   └── settings.py             # Alert thresholds & Gemini API key manager
├── data/                       # Local SQLite auth database (auto-created)
├── models/                     # Checkpoints (e.g. e-waste YOLO weights)
├── requirements.txt            # Main Python dependencies
├── .env                        # Local secrets & API keys (do not commit)
└── README.md                   # Project documentation
```

---

## 🚀 Step-by-Step Setup Guide

Follow these simple steps in your terminal to get EcoTwin running on your local machine:

### 1. Clone the Repository

Open your terminal or PowerShell and run:

```bash
git clone https://github.com/your-username/CodeClash2.0_DSU.git
cd CodeClash2.0_DSU
```

*(Replace the URL with your actual repository remote if different).*

---

### 2. Create and Activate a Virtual Environment

It is recommended to use **Python 3.10+**.

#### On Windows (PowerShell):
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

> **Note:** If PowerShell gives a script execution policy error, run this first:
> ```powershell
> Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
> .\.venv\Scripts\Activate.ps1
> ```

#### On macOS / Linux:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

---

### 3. Install Dependencies

Upgrade `pip` and install all required packages:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

---

### 4. Configure Environment Variables (`.env`)

Create a `.env` file in the project root directory.

#### Windows (PowerShell):
```powershell
New-Item -ItemType File -Path .env -Force
```

#### macOS / Linux:
```bash
touch .env
```

Open `.env` in your text editor and add:

```dotenv
ECOTWIN_AUTH_DB=data/auth.sqlite3
GEMINI_API_KEY=your_gemini_api_key_here
```

> 💡 **Where do I get a Gemini API Key?**
> You can get a free API key in 30 seconds from [Google AI Studio](https://aistudio.google.com/app/apikey).
> *(Note: If you leave `GEMINI_API_KEY` blank, the app runs gracefully in simulated AI mode).*

---

### 5. Create Your Admin Account

Initialize the local authentication database by creating your admin login:

```bash
python -m core.auth create-admin
```

You will be prompted to enter an **admin username** and **password**.

---

### 6. Run the Application

Launch the Streamlit web dashboard:

```bash
streamlit run app.py
```

Streamlit will print the local access URL:
```text
  Local URL: http://localhost:8501
  Network URL: http://192.168.x.x:8501
```

Open **`http://localhost:8501`** in your browser and log in with your admin credentials! 🎉

---

## 🎮 How to Use EcoTwin

Once logged in, explore the key features through the left sidebar:

| Page / Feature | What You Can Do |
| :--- | :--- |
| **Overview** | View top-level network metrics, 4 live smart bins, critical warnings, and the **AI Routing Recommendations** panel. |
| **Plan Route with Gemini** | In the Overview panel, click **"Plan route with Gemini"** to generate an AI collection sequence with rationale and carbon savings. |
| **✦ EcoTwin AI Copilot** | Scroll to the bottom of Overview to ask Gemini questions about network status, thermal spikes, or battery drain. |
| **Simulate Waste Deposit** | Click **"Simulate waste deposit"** in the sidebar to simulate a waste deposit event. Notice the **AI Environmental Guidance** with circular tips! |
| **Waste Segregation** | Turn on your intake camera or upload an image of a waste item. Click **"Classify item"** to detect it with YOLOv8 and view disposal guidance. |
| **Sensors** | Inspect ultrasonic air gap readings, manual test distance inputs, and real-time fill level changes. |
| **Bin Network & Map** | Filter smart bins by status, dispatch collection trucks, or view geographic coordinates on the city map. |
| **Settings** | Adjust the full-bin alert threshold and easily update/test your **Gemini API key** directly in the UI. |

---

## 🔮 Roadmap & Future Enhancements

- **Physical Hardware Hookup:** Connect ultrasonic distance sensors (HC-SR04) and microcontrollers (ESP32 / Raspberry Pi) via MQTT or REST API.
- **Dedicated Custom Weights:** Train waste-specific models using the included TACO dataset scripts (`scripts/prepare_taco.py`).
- **Autonomous Dispatch Integration:** Connect Gemini routing proposals directly to driver navigation apps (e.g. Google Maps API / Leaflet).
- **Time-Series Telemetry Store:** Migrate in-memory history to PostgreSQL / TimescaleDB for long-term municipal analytics.

---

## 📄 License & Credits

Built during **CodeClash 2.0 (Problem Track 1)**.  
Open-source under the [MIT License](LICENSE).