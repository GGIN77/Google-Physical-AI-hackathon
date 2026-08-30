# Onakali Referee

A playful but powerful AI-powered officiating system for traditional Onam games, designed to bring precision, energy, and fairness to local sports events.

Onakali Referee combines physical sensing, real-time rule evaluation, and local AI commentary to turn classic games into a data-driven, interactive experience. From tug-of-war tension to musical-chair chaos, the platform captures motion, detects winners, and narrates the action using an on-device language model.

---

## Why this project matters

Traditional sports often rely on human observation, which can be subjective, slow, and inconsistent—especially during fast mechanical events. Onakali Referee addresses that gap by turning the game into a measurable system:

- sensor-based event detection
- automated rule evaluation
- instant winner confirmation
- fast, local AI-generated commentary
- physical feedback through connected hardware

The result is a compact, offline-first referee assistant that feels both practical and engaging for events, demos, and educational showcases.

---

## What the system does

This project is designed to monitor, judge, and explain a game in real time. The hardware collects motion and environment data, the backend evaluates game logic, and the AI layer converts raw results into commentary that feels lively and human.

At a high level, the flow is:

1. Hardware sensors capture motion and conditions.
2. The backend receives streamed telemetry.
3. Game logic decides whether a rule was broken or a player won.
4. Physical outputs trigger actuation such as flags, relays, or speaker control.
5. Local AI produces a match recap or live referee summary.

---

## Key features

- Multi-game judging engine for traditional Onam-style competitions
- Real-time telemetry from ESP32-based sensor systems
- Offline AI commentary using a local Ollama model
- Live monitoring dashboard for event control and match insights
- Physical actuator support for winner announcement and event feedback
- Modular architecture that can expand to more games and rules

### Included game modes

- Kamba Vali (Tug of War)
  - Measures force and rope motion through IMU and IR-based detection
  - Detects directional pull and crossing conditions

- Lemon & Spoon
  - Tracks motion spikes and finish-line timing
  - Identifies drops and completion events

- Musical Chairs
  - Uses sensor timing to evaluate reaction and elimination behavior
  - Supports quick, precise event detection in rapid-play scenarios

---

## System architecture

```text
┌──────────────────────────────┐
│        Physical Hardware     │
│ ESP32 + Sensors + Relays     │
│ MPU6050, IR, Ultrasonic, etc │
└──────────────┬───────────────┘
               │
               │ sensor data / serial stream
               ▼
┌──────────────────────────────┐
│      Python Game Backend     │
│ Rule engine + telemetry flow │
│ + match state management     │
└──────────────┬───────────────┘
               │
               │ local API / control layer
               ▼
┌──────────────────────────────┐
│     Local AI Commentary      │
│ Ollama + Gemma 2B (offline)  │
└──────────────┬───────────────┘
               │
               │ match recap & live narration
               ▼
┌──────────────────────────────┐
│   Live Control Dashboard     │
│  Streamlit / event UI        │
└──────────────────────────────┘
```

---

## Tech stack

- Embedded hardware: ESP32
- Sensors: IMU, IR, ultrasonic, relay, servo, GPIO-based input/output
- Backend: Python
- Visualization/control: Streamlit
- Local AI: Ollama with Gemma 2B
- Communication: serial telemetry and local API integration

This combination keeps the system lightweight, interactive, and suitable for offline demonstrations.

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
│       ├── lemon_spoon.py
│       └── musical_chairs.py
├── firmware/
│   └── onakali_firmware.ino
└── .gitignore
```

---

## Getting started

### Prerequisites

- Python environment for the backend
- ESP32 development setup for firmware flashing
- Ollama installed for local model inference
- A compatible local machine for running the UI and backend together

### 1. Set up the local model

Install Ollama and pull the model used for match narration and commentary.

```bash
ollama pull gemma2:2b
```

### 2. Prepare the Python environment

Create a virtual environment and install the project dependencies from the repository requirements file.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Run the backend and dashboard

Use the Python backend and dashboard components inside the backend folder to start the live judging flow and Web UI.

### 4. Flash the firmware

Program the ESP32 with the firmware in the firmware directory and connect the required sensors and actuators.

---

## Typical workflow

1. Connect the ESP32 hardware and sensors.
2. Start the backend telemetry service.
3. Launch the game dashboard.
4. Begin a match and monitor live readings.
5. Let the rules engine determine the winner.
6. Generate AI commentary for the outcome.
7. Trigger the physical announcement or actuation sequence.

---

## Why it stands out

Onakali Referee blends the energy of traditional games with the precision of modern embedded systems and local AI. Instead of merely measuring a sport, it makes the sport feel alive: it reacts, records, judges, and tells the story.

That combination makes it especially compelling for:

- hackathons and prototype demos
- cultural event technology showcases
- educational robotics and AI projects
- local sports digitization experiments

---

## Future possibilities

This project is a strong foundation for a broader sports-tech platform. Potential next steps include:

- more game rules and event types
- richer leaderboards and match history
- improved visual analytics for sensor streams
- support for more microcontrollers or wireless modules
- multilingual referee summaries

---

## License

This project is currently shared as a prototype and can be adapted for educational, experimental, or local event use.

> For a final version, add the exact license you intend to publish under, such as MIT or Apache 2.0.

---

## Summary

Onakali Referee is more than a hardware demo—it is a complete concept for bringing fairness, intelligence, and excitement to traditional games using modern sensing and AI. It shows how local computing, embedded systems, and language models can combine to create a memorable event experience.
