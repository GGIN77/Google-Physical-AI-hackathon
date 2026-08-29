#  Onakali Referee

An automated, AI-powered sports referee and live commentary platform designed for traditional **Onakalikal** (Onam sports games). 

This project fuses **ESP32 IoT telemetry**, a **Streamlit real-time control console**, and **Gemma 2B running locally via Ollama** to deliver offline game evaluation, physical victory actuation, and automated referee commentary.

---

##  Table of Contents

- About The Project
- Key Features
- System Architecture
- Tech Stack
- Hardware Setup & Pinouts
- Repository Structure
- Getting Started
  - Prerequisites
  - Hardware Setup
  - Ollama & Gemma Setup
  - Dashboard Installation
- Usage
- License

---

##  About The Project

Refereeing traditional games often involves subjective line calls and rapid physical events that are hard to judge accurately by eye. **Onakali Referee** brings precision telemetry and automated officiating to traditional events without requiring cloud servers or active internet connections.

The system streams high-frequency sensor readings from an ESP32 microcontroller into a Python game engine that evaluates victory conditions. Upon match completion, match data is processed by **Gemma 2B** running on-device to produce localized match recaps on an interactive web UI.

---

##  Key Features

- **Multi-Game Rules Engine**:
  -  **Kamba Vali (Tug of War)**: Evaluates 3-axis rope pull dynamics (MPU6050 IMU) and line crossing via dual IR sensors.
  -  **Lemon & Spoon**: Detects drop-jerk spikes ($\vert{}a[t] - a[t-1]\vert{} > 3.5g$) and finish line elapsed times.
  -  **Musical Chairs**: Measures microsecond reaction latency using an HC-SR04 ultrasonic distance sensor triggered upon audio relay cutoff.
- **Automated Actuation**: Triggers physical prop responses, such as raising victory flags via an SG90 servo or cutting speaker power using a 5V relay.
- **Offline AI Commentary**: Uses a local Ollama server running `gemma2:2b` to generate contextual, high-energy referee summaries in under 2 seconds.
- **Real-Time Telemetry Dashboard**: Streamlit interface rendering live sensor streams, match controls, winner banners, and match logs.

---

## 📐 System Architecture

```text
  ┌───────────────────────┐
  │   Physical Hardware   │
  │ ESP32 + MPU6050 + IR  │
  └──────────┬────────────┘
             │ (USB Serial / 115200 Baud / JSON @ 25Hz)
             ▼
  ┌───────────────────────┐
  │    Python Backend     │
  │ Streamlit + Engine    │
  └──────────┬────────────┘
             │ (HTTP REST API / Localhost:11434)
             ▼
  ┌───────────────────────┐
  │    Local AI Server    │
  │  Ollama (Gemma 2B)    │
  └───────────────────────┘
