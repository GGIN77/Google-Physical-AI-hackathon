import sys
import os

# Ensure backend root folder is in system path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import json
import time
import pandas as pd
from serial_manager import SerialManager
from ai.referee_ai import generate_commentary

# Page Configuration
st.set_page_config(
    page_title="Onakali Referee Dashboard",
    page_icon="🌼",
    layout="wide"
)

# Custom CSS for Festive Onam UI Styling
st.markdown("""
<style>
    /* Main Background & Fonts */
    .stApp {
        background: linear-gradient(135deg, #FFFDF0 0%, #F5E6CA 100%);
        color: #2D1E18;
    }
    
    /* Festive Title Header */
    .festive-header {
        background: linear-gradient(90deg, #D4AF37, #8B0000);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        font-size: 2.2rem !important;
        margin-bottom: 0px;
        text-align: center;
    }

    /* Cards Styling */
    .css-card {
        background: rgba(255, 255, 255, 0.75);
        border-radius: 16px;
        padding: 20px;
        box-shadow: 0 8px 32px 0 rgba(139, 0, 0, 0.08);
        backdrop-filter: blur(8px);
        border: 1px solid rgba(212, 175, 55, 0.3);
        margin-bottom: 20px;
    }

    /* Custom Metric Badges */
    .status-badge {
        background-color: #8B0000;
        color: #FFD700;
        padding: 6px 14px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.95rem;
        display: inline-block;
        border: 1px solid #D4AF37;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Session States
if "serial" not in st.session_state:
    st.session_state.serial = SerialManager()
if "current_game" not in st.session_state:
    st.session_state.current_game = "KAMBA_VALI"
if "telemetry_log" not in st.session_state:
    st.session_state.telemetry_log = []
if "game_active" not in st.session_state:
    st.session_state.game_active = False

# Sidebar Configuration
st.sidebar.markdown("### 🎮 Onakali Control Panel")

port = st.sidebar.text_input("Serial Port", value="COM3")
conn_col1, conn_col2 = st.sidebar.columns(2)

with conn_col1:
    if st.sidebar.button("🔌 Connect"):
        if st.session_state.serial.connect(port, 115200):
            st.sidebar.success(f"Connected: {port}")
        else:
            st.sidebar.error("Connection Failed")

with conn_col2:
    if st.sidebar.button("❌ Disconnect"):
        st.session_state.serial.disconnect()
        st.sidebar.info("Disconnected")

st.sidebar.divider()

# Game Mode Selector
st.sidebar.markdown("#### 🎯 Select Game Mode")
selected_game = st.sidebar.selectbox(
    "Active Game", 
    ["KAMBA_VALI", "LEMON_SPOON", "MUSICAL_CHAIRS"],
    label_visibility="collapsed"
)

# Dynamic Hardware Game Switcher (FIXT: st.toast used directly instead of st.sidebar.toast)
if selected_game != st.session_state.current_game:
    st.session_state.current_game = selected_game
    cmd = json.dumps({"command": "SET_MODE", "mode": selected_game}) + "\n"
    st.session_state.serial.send(cmd)
    st.toast(f"Mode set to: {selected_game}")

st.sidebar.divider()

# Game Execution Buttons
col_start, col_reset = st.sidebar.columns(2)
with col_start:
    if st.button("▶ START", type="primary", use_container_width=True):
        st.session_state.telemetry_log = []
        st.session_state.game_active = True
        cmd = json.dumps({"command": "START"}) + "\n"
        st.session_state.serial.send(cmd)
        st.sidebar.warning("Match Live!")

with col_reset:
    if st.button("↺ RESET", use_container_width=True):
        st.session_state.game_active = False
        st.session_state.telemetry_log = []
        cmd = json.dumps({"command": "RESET"}) + "\n"
        st.session_state.serial.send(cmd)

# Scaled Local Banner Image Display
onam_image_path = r"C:\Users\nevin\Downloads\onam pic.jpeg"
if os.path.exists(onam_image_path):
    img_col1, img_col2, img_col3 = st.columns([1, 1.8, 1])
    with img_col2:
        st.image(onam_image_path, width=420)
else:
    st.warning(f"Image not found at {onam_image_path}. Please check the filename.")

# Header Section
st.markdown('<h1 class="festive-header">🏆 ONAKALI AI REFEREE DASHBOARD</h1>', unsafe_allow_html=True)
st.markdown(f"<div style='text-align: center; margin-bottom: 25px;'><b>Active Mode:</b> <span class='status-badge'>{st.session_state.current_game}</span></div>", unsafe_allow_html=True)

# Layout Split: Telemetry Chart vs AI Commentary
col_chart, col_ai = st.columns([1.8, 1.2])

with col_chart:
    st.markdown("### 📈 Live Telemetry Feed")
    chart_placeholder = st.empty()
    status_placeholder = st.empty()

with col_ai:
    st.markdown("### 🤖 Gemma AI Commentary")
    ai_placeholder = st.empty()
    ai_placeholder.info("Waiting for match completion to run local LLM evaluation...")

# Data Ingestion & Live Update Loop
if st.session_state.game_active:
    new_data = st.session_state.serial.read_queue()
    if new_data:
        for entry in new_data:
            st.session_state.telemetry_log.append(entry)
            
            # Outcome Trigger
            if entry.get("state") == "RESULT" or entry.get("winner"):
                st.session_state.game_active = False
                st.balloons()
                
                # Actuate flag on hardware via Servo
                servo_cmd = json.dumps({"command": "SERVO", "angle": 90}) + "\n"
                st.session_state.serial.send(servo_cmd)
                
                # Request AI Commentary from Gemma 2B
                with st.spinner("Gemma is evaluating match telemetry..."):
                    commentary = generate_commentary(
                        game=st.session_state.current_game,
                        event_log=st.session_state.telemetry_log
                    )
                    ai_placeholder.markdown(f"### 📣 Verdict:\n\n{commentary}")

    # Render Live Acceleration or Distance Data
    if st.session_state.telemetry_log:
        df = pd.DataFrame(st.session_state.telemetry_log)
        if "ax" in df.columns:
            chart_placeholder.line_chart(df[["ax", "ay", "az"]].tail(50))
        elif "distance" in df.columns:
            chart_placeholder.line_chart(df[["distance"]].tail(50))
            
    time.sleep(0.04)