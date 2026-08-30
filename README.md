# Onakali Referee

An AI-powered officiating system for traditional Onam games, combining embedded hardware, computer vision, real-time rule evaluation, and local AI to make games more measurable, interactive, and fair.

Onakali Referee currently focuses on two game modes: **Kamba Vali (Tug of War)** and **Lemon & Spoon**. The system combines ESP32-based sensing with an ESP32-CAM, Python-based game logic, OpenCV computer vision, and a locally running Gemma 3 4B model through Ollama.

---

## Why this project matters

Traditional games often rely entirely on human observation. During fast-paced events, this can make judging difficult, subjective, or inconsistent.

Onakali Referee addresses this by converting physical events into measurable data:

* sensor-based event detection
* camera-based object and motion detection
* automated rule evaluation
* real-time event detection
* local AI verification and commentary
* physical feedback through connected hardware

The system is designed to work locally, making it suitable for demonstrations and environments where an internet connection is not required.

---

## What the system does

Onakali Referee combines three main layers:

1. **Embedded sensing** — ESP32 hardware collects physical events using sensors.
2. **Computer vision and rule processing** — Python processes camera frames and sensor data to determine game events.
3. **Local AI** — Gemma 3 4B running through Ollama provides additional visual verification and referee commentary.

The general workflow is:

```text
Physical Game
     │
     ├── ESP32 + Sensors
     │
     └── ESP32-CAM
             │
             ▼
       Python Backend
             │
       ┌─────┴─────┐
       │           │
   Game Rules   Computer Vision
       │           │
       └─────┬─────┘
             ▼
       Event Detection
             │
             ▼
       Gemma 3 4B
       via Ollama
             │
             ▼
     Referee Decision
             │
             ▼
      Streamlit Dashboard
```

---

## Key features

* Multi-game judging framework for traditional Onam competitions
* Real-time telemetry from ESP32-based hardware
* ESP32-CAM based visual monitoring
* OpenCV-based object and motion detection
* Local AI verification using Ollama and Gemma 3 4B
* Automated game-event detection
* Live monitoring dashboard
* Physical actuator support
* Offline-first architecture
* Modular game-engine structure

---

## Included game modes

### Kamba Vali — Tug of War

Kamba Vali uses ESP32-based sensing to monitor physical movement and determine game events.

The system can use:

* IR-based detection
* IMU-based motion sensing
* directional movement
* crossing conditions
* sensor telemetry

The collected data is processed by the Python game engine to determine the state of the match.

### Lemon & Spoon

Lemon & Spoon uses an **ESP32-CAM** to provide a live camera feed to the Python computer-vision system.

The current detection pipeline works as follows:

```text
ESP32-CAM
    │
    │ JPEG frames over Wi-Fi
    ▼
Python
    │
    ▼
OpenCV
    │
    ├── HSV color filtering
    ├── Yellow-object detection
    ├── Contour detection
    ├── Shape filtering
    └── Center-point tracking
    │
    ▼
Motion Analysis
    │
    ├── Position
    ├── Direction
    └── Downward velocity
    │
    ▼
Possible Fall
    │
    ▼
Gemma 3 4B
    │
    ▼
Visual verification
```

The computer-vision system identifies the detected object's center and tracks its movement between frames. A rapid downward movement combined with the configured fall conditions can trigger a suspected fall.

Gemma 3 4B can then be used as an additional verification layer rather than relying solely on motion detection.

The current implementation does not require a custom-trained lemon model. The initial vision stage uses color, contour, shape, and motion information.

---

## System architecture

```text
┌─────────────────────────────────┐
│       Physical Hardware         │
│                                 │
│ ESP32 + Sensors                 │
│ IR  / GPIO                      │
│                                 │
│ ESP32-CAM                       │
│ Camera-based monitoring         │
└───────────────┬─────────────────┘
                │
                │ Serial / Wi-Fi
                ▼
┌─────────────────────────────────┐
│        Python Backend           │
│                                 │
│ Telemetry                       │
│ Game Engine                     │
│ Rule Evaluation                 │
│ Match State                     │
└───────────────┬─────────────────┘
                │
                ├──────────────────┐
                │                  │
                ▼                  ▼
┌────────────────────────┐  ┌────────────────────────┐
│   Computer Vision      │  │     Local AI           │
│                        │  │                        │
│ OpenCV                 │  │ Ollama                 │
│ Object Detection       │  │ Gemma 3 4B             │
│ Motion Tracking        │  │ Visual Verification    │
│ Fall Detection         │  │ Referee Commentary     │
└────────────┬───────────┘  └────────────┬───────────┘
             │                           │
             └─────────────┬─────────────┘
                           ▼
                ┌────────────────────────┐
                │   Streamlit Dashboard  │
                │                        │
                │ Live Game Status       │
                │ Detection Results      │
                │ Match Information      │
                │ AI Commentary          │
                └────────────────────────┘
```

---

## Tech stack

### Hardware

* ESP32
* ESP32-CAM
* IR sensors
* Servo / actuator components
* GPIO-based inputs and outputs

### Software

* Python
* OpenCV
* NumPy
* Flask
* Streamlit
* Ollama
* Gemma 3 4B

### Computer vision

* OpenCV
* HSV color segmentation
* Contour detection
* Shape filtering
* Object center tracking
* Motion and velocity analysis

### AI

* Ollama
* Gemma 3 4B
* Local/offline inference

This architecture keeps the core processing local and avoids requiring an external cloud AI service.

---

## Repository structure

```text
onamhackathon/
├── README.md
├── requirements.txt
├── backend/
│   ├── app.py
│   ├── serial_manager.py
│   ├── ai/
│   │   ├── __init__.py
│   │   ├── prompts.py
│   │   └── referee_ai.py
│   └── game_engine/
│       ├── __init__.py
│       ├── base_game.py
│       ├── kamba_vali.py
│       └── lemon_spoon.py
├── firmware/
│   └── onakali_firmware.ino
└── .gitignore
```

---

## Getting started

### Prerequisites

* Python 3.11
* ESP32 development environment
* ESP32-CAM
* Ollama
* A local computer capable of running Python, OpenCV, and Gemma 3 4B
* Required sensors and actuators for the selected game

### 1. Install the Python dependencies

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it:

Linux/macOS:

```bash
source .venv/bin/activate
```

Windows:

```powershell
.venv\Scripts\activate
```

Install the dependencies:

```bash
pip install -r requirements.txt
```

### 2. Set up Ollama

Install Ollama and download the local Gemma model:

```bash
ollama pull gemma3:4b
```

Verify that it is available:

```bash
ollama list
```

You should see:

```text
gemma3:4b
```

### 3. Configure the ESP32-CAM

Flash the ESP32-CAM firmware and connect it to the same local network as the computer running the Python vision system.

The ESP32-CAM provides JPEG frames through its local HTTP camera endpoint.

### 4. Configure the Python backend

Configure the appropriate ESP32-CAM address and hardware communication settings in the backend.

The Python system receives camera frames, processes sensor telemetry, evaluates game rules, and communicates with the local AI layer.

### 5. Start the application

Start the backend and Streamlit dashboard using the project's configured entry points.

---

## Lemon & Spoon detection pipeline

The Lemon & Spoon system does not currently require a trained lemon-detection model.

The initial vision system uses OpenCV:

```text
Camera Frame
     │
     ▼
Resize / Preprocessing
     │
     ▼
BGR → HSV
     │
     ▼
Yellow Color Mask
     │
     ▼
Morphological Filtering
     │
     ▼
Contour Detection
     │
     ▼
Area + Shape Filtering
     │
     ▼
Object Center
     │
     ▼
Position Tracking
     │
     ▼
Downward Motion / Velocity
     │
     ▼
Possible Fall
     │
     ▼
Gemma 3 4B Verification
```

This approach allows the system to be developed and tested before a custom lemon dataset is available.

A custom-trained object-detection model can be added later if greater lemon-specific detection accuracy is required.

---

## Typical workflow

1. Connect the ESP32 hardware and required sensors.
2. Connect the ESP32-CAM for Lemon & Spoon.
3. Start Ollama with the `gemma3:4b` model available locally.
4. Start the Python backend.
5. Launch the Streamlit dashboard.
6. Begin a match.
7. Monitor sensor telemetry and camera detections.
8. Let the game engine evaluate the relevant rules.
9. Use computer vision to detect visual events such as object movement or drops.
10. Use Gemma 3 4B for AI-based verification and referee commentary.
11. Display the result through the dashboard.
12. Trigger connected physical outputs when required.

---

## Why it stands out

Onakali Referee combines traditional games with embedded systems, computer vision, and local AI.

Instead of relying entirely on human observation, the system creates a measurable digital representation of game events.

It combines:

* physical sensing
* computer vision
* real-time rule evaluation
* local AI
* hardware control
* live visualization

The offline-first design also makes it suitable for demonstrations where reliable internet connectivity is not guaranteed.

---

## Future possibilities

Potential future improvements include:

* custom-trained lemon detection
* more robust object tracking
* improved fall prediction
* automatic calibration of camera zones
* additional traditional games
* richer match history and leaderboards
* improved visual analytics
* multilingual referee commentary
* wireless communication between multiple ESP32 devices
* automatic event replay and analysis

---

## License

This project is currently shared as a prototype and can be adapted for educational, experimental, or local event use.

> For a final version, add the exact license you intend to publish under, such as MIT or Apache 2.0.

---

## Summary

Onakali Referee is a prototype platform for bringing modern sensing, computer vision, embedded systems, and local AI to traditional Onam games.

By combining ESP32 hardware, ESP32-CAM visual monitoring, Python-based rule evaluation, OpenCV, and Gemma 3 4B through Ollama, the system can observe game events, evaluate them, verify important decisions, and present the results through a live referee dashboard.
