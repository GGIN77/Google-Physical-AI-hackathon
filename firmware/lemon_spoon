import cv2
import urllib.request
import numpy as np
import threading
import time
from collections import deque

# ============================================================
# INSTALL REQUIRED PACKAGES
# ============================================================
# pip install opencv-python ollama flask numpy
#
# Also run:
#   ollama pull gemma3:4b
# ============================================================

import ollama
from flask import Flask, Response, jsonify


# ============================================================
# CAMERAS
#
# Add one entry per ESP32-CAM. Each camera is tracked completely
# independently (its own lemon, its own timer, its own Gemma
# checks). The webpage will automatically show one panel per
# camera plus a leaderboard comparing them.
# ============================================================

CAMERAS = [
    {
        "id": "cam1",
        "name": "Camera 1",
        "url": "http://10.25.172.137/cam-lo.jpg",
    },

    # Add more cameras like this:
    # {
    #     "id": "cam2",
    #     "name": "Camera 2",
    #     "url": "http://10.25.172.xxx/cam-lo.jpg",
    # },
]


# ============================================================
# WEB SERVER SETTINGS
# ============================================================

WEB_HOST = "0.0.0.0"
WEB_PORT = 5000

# Show a local cv2.imshow() debug window per camera in addition to
# the webpage. Turn this off if you run many cameras or hit GUI
# threading issues on your platform.
SHOW_LOCAL_WINDOWS = True


# ============================================================
# GEMMA SETTINGS
# ============================================================

GEMMA_MODEL = "gemma3:4b"

# --- Fall verification ---
VERIFY_PROMPT = (
    "Look carefully at this image. A lemon may have just fallen. "
    "Respond in exactly two lines:\n"
    "Line 1: YES or NO - does this image show a lemon that has "
    "fallen or is currently falling downward?\n"
    "Line 2: One short sentence explaining what you see."
)

# --- Periodic identity / quality check ---
IDENTITY_PROMPT = (
    "Look at the round yellow object in the center of this image, "
    "inside the yellow bounding box. Respond in exactly two lines:\n"
    "Line 1: YES or NO - is this actually a lemon (and not a hand, "
    "toy, wall, light, or other yellow object)?\n"
    "Line 2: One short phrase describing the lemon's ripeness, color, "
    "or condition."
)

IDENTITY_CHECK_INTERVAL_SECONDS = 4.0


# ============================================================
# YELLOW BALL DETECTION SETTINGS
# ============================================================

LOWER_YELLOW = np.array([20, 100, 100])
UPPER_YELLOW = np.array([40, 255, 255])

MIN_CONTOUR_AREA = 150
MAX_CONTOUR_AREA = 30000

# A crumpled paper ball is never as perfectly round as a lemon, and
# its jagged outline makes raw circularity read lower and noisier
# frame-to-frame. 0.55 is tuned for a smooth lemon; drop it if you
# still see dropouts (try 0.40-0.45 for paper).
MIN_CIRCULARITY = 0.45

PROCESS_WIDTH = 320


# ============================================================
# DETECTION STABILITY SETTINGS
#
# A paper ball's matte, textured surface fragments the yellow mask
# more than a lemon's smooth peel does, which is what causes the
# detected / not-detected jitter. These two settings smooth that
# out without touching the fall-detection math itself.
# ============================================================

# Morphological "close" kernel size - fills small holes/gaps in the
# mask so a crumpled ball doesn't look like several small blobs.
# Bump this up (e.g. 9-11) if the mask still looks fragmented.
MASK_CLOSE_KERNEL = 7

# If the ball isn't found for a frame or two, keep showing it at its
# last known position for up to this long instead of immediately
# flickering to "NOT DETECTED". Must stay well under
# OUT_OF_FRAME_GRACE_SECONDS so a real fall/removal still registers.
DETECTION_HOLD_SECONDS = 0.25


# ============================================================
# FALL DETECTION SETTINGS
# ============================================================

FALL_LINE = 180

POSITION_HISTORY = 10
HISTORY_WINDOW_SECONDS = 0.5

FALL_VELOCITY_THRESHOLD = 250

FALL_COOLDOWN_SECONDS = 2.0

EMA_ALPHA = 0.6

OUT_OF_FRAME_GRACE_SECONDS = 0.8


# ============================================================
# SHARED WEB STATE
#
# One entry per camera id. Written by each camera's worker thread,
# read by the Flask routes. Protected by web_lock.
# ============================================================

web_lock = threading.Lock()

# cam_id -> latest JPEG bytes
latest_jpeg = {}

# cam_id -> status dict shown on the webpage
latest_status = {}


def _blank_status(name):
    return {
        "name": name,
        "state": "starting",
        "velocity": 0,
        "commentary": "",
        "identity_result": None,
        "identity_commentary": "",
        # --- timer fields ---
        "current_stay_seconds": 0.0,   # live: how long THIS lemon has been sitting there right now
        "last_stay_seconds": 0.0,      # how long the PREVIOUS lemon stayed before it fell
        "best_stay_seconds": 0.0,      # longest stay recorded on this camera so far
        "fall_count": 0,
        "updated_at": 0,
    }


for _cam in CAMERAS:
    latest_status[_cam["id"]] = _blank_status(_cam["name"])
    latest_jpeg[_cam["id"]] = None


def format_duration(seconds):
    seconds = max(0, int(seconds))
    minutes = seconds // 60
    secs = seconds % 60
    return f"{minutes}:{secs:02d}"


# ============================================================
# GEMMA HELPERS
#
# Both return plain values instead of touching globals, so they are
# safe to call from any camera's background thread.
# ============================================================

def ask_gemma_fall(frame_bgr):
    """Returns (confirmed: bool, commentary: str)."""

    try:
        ok, buffer = cv2.imencode(".jpg", frame_bgr)

        if not ok:
            return False, "Could not encode image for verification."

        response = ollama.chat(
            model=GEMMA_MODEL,
            messages=[{
                "role": "user",
                "content": VERIFY_PROMPT,
                "images": [buffer.tobytes()]
            }]
        )

        raw = response["message"]["content"].strip()

        lines = [line.strip() for line in raw.splitlines() if line.strip()]
        verdict_line = lines[0].upper() if lines else ""
        commentary_line = lines[1] if len(lines) > 1 else raw

        return verdict_line.startswith("YES"), commentary_line

    except Exception as e:
        print("Gemma fall-check error:", e)
        # If Gemma fails, trust motion detection
        return True, "AI unavailable - fall confirmed by motion detection."


def ask_gemma_identity(frame_bgr):
    """Returns (result: bool|None, commentary: str)."""

    try:
        ok, buffer = cv2.imencode(".jpg", frame_bgr)

        if not ok:
            return None, "Could not encode image for identity check."

        response = ollama.chat(
            model=GEMMA_MODEL,
            messages=[{
                "role": "user",
                "content": IDENTITY_PROMPT,
                "images": [buffer.tobytes()]
            }]
        )

        raw = response["message"]["content"].strip()

        lines = [line.strip() for line in raw.splitlines() if line.strip()]
        verdict_line = lines[0].upper() if lines else ""
        commentary_line = lines[1] if len(lines) > 1 else raw

        return verdict_line.startswith("YES"), commentary_line

    except Exception as e:
        print("Gemma identity-check error:", e)
        return None, "AI identity check unavailable."


# ============================================================
# BACKGROUND ESP32-CAM FRAME GRABBER
# ============================================================

class FrameGrabber:

    def __init__(self, camera_url, name="camera"):
        self.url = camera_url
        self.name = name
        self.frame = None
        self.lock = threading.Lock()
        self.running = True
        self.thread = threading.Thread(target=self._update, daemon=True)
        self.thread.start()

    def _update(self):

        while self.running:

            try:
                response = urllib.request.urlopen(self.url, timeout=3)
                data = response.read()

                image = cv2.imdecode(
                    np.frombuffer(data, dtype=np.uint8),
                    cv2.IMREAD_COLOR
                )

                if image is not None:
                    with self.lock:
                        self.frame = image

            except Exception as e:
                print(f"[{self.name}] ESP32-CAM error:", e)
                time.sleep(0.2)

    def get_frame(self):
        with self.lock:
            if self.frame is None:
                return None
            return self.frame.copy()

    def stop(self):
        self.running = False


# ============================================================
# PER-CAMERA WORKER
#
# Runs the full detect -> track -> verify -> time pipeline for one
# camera. Every camera gets its own instance, its own lemon, and
# its own timer, so multiple lemons on multiple cameras never
# interfere with each other.
# ============================================================

class CameraWorker(threading.Thread):

    def __init__(self, cam_config):
        super().__init__(daemon=True)

        self.id = cam_config["id"]
        self.name = cam_config["name"]
        self.url = cam_config["url"]

        self.grabber = FrameGrabber(self.url, name=self.name)

        # --- ball tracking state ---
        self.y_history = deque(maxlen=POSITION_HISTORY)
        self.smoothed_y = None

        self.fall_detected = False
        self.fall_time = 0

        self.last_seen_time = 0
        self.ball_seen_before = False
        self.last_box = None   # (x, y, w, h) of the last real detection

        # --- fall verification (Gemma task 1) ---
        self.verifying = False
        self.verify_result = None
        self.gemma_commentary = ""

        # --- identity / quality check (Gemma task 2) ---
        self.identity_checking = False
        self.identity_result = None
        self.identity_commentary = ""
        self.last_identity_check_time = 0.0

        # --- stay timer ---
        self.session_start_time = None   # when the CURRENT lemon first appeared
        self.last_stay_seconds = 0.0
        self.best_stay_seconds = 0.0
        self.fall_count = 0

        # --- fps ---
        self.fps_counter = 0
        self.fps_timer = time.time()
        self.fps_display = 0

        self.running = True

    # --------------------------------------------------------
    # MAIN LOOP
    # --------------------------------------------------------

    def run(self):

        print(f"[{self.name}] Waiting for camera...")

        while self.running and self.grabber.get_frame() is None:
            time.sleep(0.05)

        print(f"[{self.name}] CONNECTED!")

        while self.running:
            self._process_one_frame()

        self.grabber.stop()

        if SHOW_LOCAL_WINDOWS:
            try:
                cv2.destroyWindow(self.name)
            except Exception:
                pass

    def stop(self):
        self.running = False

    # --------------------------------------------------------
    # ONE FRAME
    # --------------------------------------------------------

    def _process_one_frame(self):

        raw_frame = self.grabber.get_frame()

        if raw_frame is None:
            time.sleep(0.01)
            return

        now = time.time()

        # ================================================
        # RESIZE FRAME
        # ================================================

        if PROCESS_WIDTH is not None:
            scale = PROCESS_WIDTH / raw_frame.shape[1]
            im = cv2.resize(
                raw_frame,
                (PROCESS_WIDTH, int(raw_frame.shape[0] * scale))
            )
        else:
            im = raw_frame.copy()

        height, width = im.shape[:2]

        # ================================================
        # YELLOW BALL DETECTION (OpenCV owns this entirely)
        # ================================================

        blurred = cv2.GaussianBlur(im, (7, 7), 0)
        hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, LOWER_YELLOW, UPPER_YELLOW)

        # Close small holes/gaps first - a crumpled paper ball's
        # texture and creases otherwise split it into several
        # smaller blobs that flicker in and out of the area/
        # circularity thresholds independently.
        close_kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE, (MASK_CLOSE_KERNEL, MASK_CLOSE_KERNEL)
        )
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, close_kernel)

        mask = cv2.erode(mask, None, iterations=1)
        mask = cv2.dilate(mask, None, iterations=2)

        contours, _ = cv2.findContours(
            mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        best_contour = None
        best_area = 0

        for contour in contours:

            area = cv2.contourArea(contour)

            if area < MIN_CONTOUR_AREA or area > MAX_CONTOUR_AREA:
                continue

            # Measure circularity against the convex hull rather
            # than the raw contour. A crumpled ball's outline is
            # jagged, which makes raw circularity dip below
            # threshold on essentially random frames - the hull is
            # a much steadier proxy for "is this basically round".
            hull = cv2.convexHull(contour)
            hull_area = cv2.contourArea(hull)
            perimeter = cv2.arcLength(hull, True)

            if perimeter == 0:
                continue

            circularity = 4 * np.pi * hull_area / (perimeter ** 2)

            if circularity < MIN_CIRCULARITY:
                continue

            if area > best_area:
                best_area = area
                best_contour = contour

        # ================================================
        # DRAW FALL LINE
        # ================================================

        cv2.line(im, (0, FALL_LINE), (width, FALL_LINE), (255, 0, 0), 2)
        cv2.putText(
            im, "FALL LINE", (10, FALL_LINE - 10),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2
        )

        # ================================================
        # GET GEMMA FALL-VERIFICATION RESULT
        # ================================================

        if self.verifying and self.verify_result is not None:

            if self.verify_result:
                print(f"[{self.name}] LEMON FALL CONFIRMED!")
                self.fall_detected = True
                self.fall_time = now
                self._finalize_stay(now)
            else:
                print(f"[{self.name}] Gemma rejected the fall.")
                self.fall_detected = False

            self.verifying = False
            self.verify_result = None
            self.y_history.clear()
            self.smoothed_y = None

        # ================================================
        # RESET AFTER COOLDOWN
        # ================================================

        if self.fall_detected and (now - self.fall_time) > FALL_COOLDOWN_SECONDS:
            self.fall_detected = False
            self.y_history.clear()
            self.smoothed_y = None

        velocity = 0
        state = "stable"

        detected_this_frame = best_contour is not None

        # A brief 1-2 frame mask dropout (crumpled paper flickering
        # in and out of the HSV/circularity thresholds) is held at
        # its last known position instead of immediately flipping
        # the UI to "NOT DETECTED" and resetting tracking state.
        held = (
            not detected_this_frame
            and self.ball_seen_before
            and not self.fall_detected
            and self.last_box is not None
            and (now - self.last_seen_time) <= DETECTION_HOLD_SECONDS
        )

        # ================================================
        # BALL DETECTED (or held through a brief dropout)
        # ================================================

        if detected_this_frame or held:

            if detected_this_frame:
                self.last_seen_time = now
                x, y, w, h = cv2.boundingRect(best_contour)
                self.last_box = (x, y, w, h)
            else:
                # Held - reuse the last real detection's box. We
                # deliberately do NOT touch last_seen_time here, so
                # OUT_OF_FRAME_GRACE_SECONDS is still measured from
                # the last genuine sighting.
                x, y, w, h = self.last_box

            # Lemon just (re)appeared - start a new stay timer
            if not self.ball_seen_before or self.session_start_time is None:
                self.session_start_time = now

            self.ball_seen_before = True

            center_x = int(x + w / 2)
            center_y = int(y + h / 2)

            if self.smoothed_y is None:
                self.smoothed_y = center_y
            elif detected_this_frame:
                self.smoothed_y = (
                    EMA_ALPHA * center_y
                    + (1 - EMA_ALPHA) * self.smoothed_y
                )
            # else: held frame, no new measurement - keep the last
            # smoothed_y as-is rather than nudging it toward a box
            # we didn't actually see this frame.

            # ============================================
            # PERIODIC IDENTITY / QUALITY CHECK (Gemma task 2)
            # ============================================

            if (
                not self.verifying
                and not self.identity_checking
                and (now - self.last_identity_check_time) > IDENTITY_CHECK_INTERVAL_SECONDS
            ):

                self.identity_checking = True
                self.last_identity_check_time = now

                pad = 20
                x0, y0 = max(x - pad, 0), max(y - pad, 0)
                x1, y1 = min(x + w + pad, width), min(y + h + pad, height)

                crop = im[y0:y1, x0:x1]

                if crop.size == 0:
                    crop = im.copy()

                threading.Thread(
                    target=self._run_identity_check,
                    args=(crop,),
                    daemon=True
                ).start()

            # ============================================
            # DRAW BALL BOX
            # ============================================

            if self.identity_result is False:
                box_color = (200, 0, 255)
                label = "UNCERTAIN"
            else:
                box_color = (0, 255, 255)
                label = "LEMON"

            if held:
                # Dim the box during a held frame so it's visually
                # obvious this position is a hold-over, not a fresh
                # detection.
                box_color = tuple(int(c * 0.5) for c in box_color)
                label += " (holding)"

            cv2.rectangle(im, (x, y), (x + w, y + h), box_color, 2)
            cv2.circle(im, (center_x, int(self.smoothed_y)), 6, (0, 0, 255), -1)
            cv2.putText(
                im, label, (x, max(y - 10, 20)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, box_color, 2
            )

            # ============================================
            # POSITION HISTORY / VELOCITY (fall math untouched
            # by identity check or the timer)
            # ============================================

            if detected_this_frame and not self.fall_detected and not self.verifying:
                self.y_history.append((now, self.smoothed_y))

            while self.y_history and (now - self.y_history[0][0]) > HISTORY_WINDOW_SECONDS:
                self.y_history.popleft()

            if len(self.y_history) >= 2:

                t_old, y_old = self.y_history[0]
                t_new, y_new = self.y_history[-1]

                dt = t_new - t_old

                if dt > 0:
                    velocity = (y_new - y_old) / dt

                if (
                    velocity > FALL_VELOCITY_THRESHOLD
                    and self.smoothed_y >= FALL_LINE
                    and not self.fall_detected
                    and not self.verifying
                ):

                    print(f"[{self.name}] Suspected ball fall: {velocity:.0f} px/s")

                    self.verifying = True
                    self.verify_result = None
                    self.gemma_commentary = ""

                    threading.Thread(
                        target=self._run_fall_check,
                        args=(raw_frame.copy(),),
                        daemon=True
                    ).start()

            # ============================================
            # DISPLAY STATE
            # ============================================

            if self.fall_detected:
                state = "eliminated"
                cv2.putText(im, "LEMON HAS FALLEN!", (10, 40),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 3)

            elif self.verifying:
                state = "verifying"
                cv2.putText(im, "VERIFYING WITH GEMMA...", (10, 40),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)

            elif self.identity_result is False:
                state = "uncertain"
                cv2.putText(im, "GEMMA UNSURE THIS IS A LEMON", (10, 40),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 0, 255), 2)

            elif velocity > 50:
                state = "moving"
                cv2.putText(im, f"LEMON MOVING {velocity:.0f} px/s", (10, 40),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

            else:
                state = "stable"
                cv2.putText(im, "LEMON STABLE", (10, 40),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            if self.identity_commentary:
                cv2.putText(im, self.identity_commentary[:60], (10, 65),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (216, 191, 216), 1)

            # Live stay timer, burned into the frame too
            live_stay = now - self.session_start_time if self.session_start_time else 0
            cv2.putText(im, f"STAY: {format_duration(live_stay)}", (10, 90),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        # ================================================
        # NO BALL DETECTED
        # ================================================

        else:

            self.identity_result = None
            self.identity_commentary = ""

            if self.fall_detected:
                state = "eliminated"
                cv2.putText(im, "LEMON HAS FALLEN!", (10, 40),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 3)

            elif (
                self.ball_seen_before
                and not self.verifying
                and (now - self.last_seen_time) > OUT_OF_FRAME_GRACE_SECONDS
            ):

                print(f"[{self.name}] Lemon fell down (out of frame)")

                self.fall_detected = True
                self.fall_time = now
                self.gemma_commentary = "Lemon disappeared from the camera frame."
                self._finalize_stay(now)

                self.ball_seen_before = False
                self.y_history.clear()
                self.smoothed_y = None

                state = "eliminated"
                cv2.putText(im, "LEMON HAS FALLEN!", (10, 40),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 3)

            else:
                state = "stable"
                cv2.putText(im, "LEMON NOT DETECTED", (10, 40),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        # ================================================
        # FPS
        # ================================================

        self.fps_counter += 1

        if now - self.fps_timer >= 1:
            self.fps_display = self.fps_counter
            self.fps_counter = 0
            self.fps_timer = now

        cv2.putText(im, f"FPS: {self.fps_display}", (width - 90, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

        # ================================================
        # PUBLISH TO WEB STATE
        # ================================================

        live_stay = (now - self.session_start_time) if self.session_start_time else 0.0

        ok, jpeg_buffer = cv2.imencode(".jpg", im)

        if ok:
            with web_lock:
                latest_jpeg[self.id] = jpeg_buffer.tobytes()
                latest_status[self.id] = {
                    "name": self.name,
                    "state": state,
                    "velocity": velocity,
                    "commentary": self.gemma_commentary,
                    "identity_result": self.identity_result,
                    "identity_commentary": self.identity_commentary,
                    "current_stay_seconds": live_stay,
                    "last_stay_seconds": self.last_stay_seconds,
                    "best_stay_seconds": self.best_stay_seconds,
                    "fall_count": self.fall_count,
                    "updated_at": now,
                }

        # ================================================
        # LOCAL DEBUG WINDOW
        # ================================================

        if SHOW_LOCAL_WINDOWS:
            try:
                cv2.imshow(self.name, im)
                cv2.waitKey(1)
            except Exception:
                pass

    # --------------------------------------------------------
    # STAY TIMER
    # --------------------------------------------------------

    def _finalize_stay(self, now):
        """Called the moment a fall is confirmed - closes out the
        timer for the lemon that just fell and updates this
        camera's personal best."""

        if self.session_start_time is None:
            return

        duration = now - self.session_start_time

        self.last_stay_seconds = duration
        self.fall_count += 1

        if duration > self.best_stay_seconds:
            self.best_stay_seconds = duration

        print(f"[{self.name}] Lemon stayed for {format_duration(duration)}")

        self.session_start_time = None

    # --------------------------------------------------------
    # GEMMA CALLBACKS
    # --------------------------------------------------------

    def _run_fall_check(self, frame_bgr):
        result, commentary = ask_gemma_fall(frame_bgr)
        self.verify_result = result
        self.gemma_commentary = commentary

    def _run_identity_check(self, frame_bgr):
        result, commentary = ask_gemma_identity(frame_bgr)
        self.identity_result = result
        self.identity_commentary = commentary
        self.identity_checking = False


# ============================================================
# FLASK WEB APP
# ============================================================

app = Flask(__name__)


def build_page_html():

    panels = ""

    for cam in CAMERAS:
        cam_id = cam["id"]
        panels += f"""
<div class="panel">

  <h2>{cam["name"]}</h2>

  <div class="status starting" id="status-{cam_id}">STARTING...</div>

  <img class="frame" id="frame-{cam_id}" src="/frame/{cam_id}.jpg">

  <div class="timer" id="timer-{cam_id}">Stay time: 0:00</div>

  <div class="subtimer" id="best-{cam_id}"></div>

  <div class="velocity" id="velocity-{cam_id}"></div>

  <div class="commentary" id="commentary-{cam_id}"></div>

  <div class="identity" id="identity-{cam_id}"></div>

</div>
"""

    cam_ids_js = ", ".join(f'"{cam["id"]}"' for cam in CAMERAS)

    return f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Lemon Detector</title>
<style>

body {{
    background: #111;
    color: white;
    font-family: Arial, sans-serif;
    padding: 25px;
}}

h1 {{ text-align: center; margin-bottom: 5px; }}

.grid {{
    display: flex;
    flex-wrap: wrap;
    gap: 25px;
    justify-content: center;
    margin-top: 20px;
}}

.panel {{
    background: #1a1a1a;
    border: 1px solid #333;
    border-radius: 12px;
    padding: 18px;
    width: 360px;
    display: flex;
    flex-direction: column;
    align-items: center;
}}

.panel h2 {{ margin: 0 0 10px 0; font-size: 1.1em; }}

.status {{
    font-size: 1.1em;
    font-weight: bold;
    padding: 8px 16px;
    border-radius: 8px;
    margin-bottom: 10px;
}}

.stable     {{ background: #1e3d1e; color: #7CFC00; }}
.moving     {{ background: #4d3d00; color: #ffd24d; }}
.verifying  {{ background: #3a2a00; color: orange; }}
.eliminated {{ background: #4d0000; color: #ff5555; }}
.uncertain  {{ background: #402a4d; color: #d59bff; }}
.starting   {{ background: #333; color: white; }}

.frame {{
    max-width: 100%;
    border: 3px solid #444;
    border-radius: 10px;
}}

.timer {{
    margin-top: 12px;
    font-size: 1.4em;
    font-weight: bold;
    color: #fff;
}}

.subtimer {{ font-size: 0.9em; color: #aaa; margin-top: 2px; }}

.velocity {{ margin-top: 6px; color: #aaa; font-size: 0.9em; }}

.commentary {{
    margin-top: 10px;
    color: #ddd;
    font-size: 0.95em;
    font-style: italic;
    text-align: center;
}}

.identity {{
    margin-top: 6px;
    color: #d59bff;
    font-size: 0.85em;
    text-align: center;
}}

table {{
    border-collapse: collapse;
    margin: 25px auto 0 auto;
    min-width: 420px;
}}

th, td {{
    padding: 10px 16px;
    border-bottom: 1px solid #333;
    text-align: left;
}}

th {{ color: #aaa; font-weight: normal; }}

tr.leader td {{ color: #7CFC00; font-weight: bold; }}

#leaderboard-title {{ text-align: center; margin-top: 35px; }}

</style>
</head>

<body>

<h1>Lemon Detector</h1>

<div class="grid">
{panels}
</div>

<h2 id="leaderboard-title">Longest Stay Leaderboard</h2>

<table>
  <thead>
    <tr>
      <th>Camera</th>
      <th>Best stay</th>
      <th>Last stay</th>
      <th>Falls seen</th>
    </tr>
  </thead>
  <tbody id="leaderboard-body">
  </tbody>
</table>

<script>

const camIds = [{cam_ids_js}];

function fmt(seconds) {{
    seconds = Math.max(0, Math.floor(seconds));
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return m + ":" + String(s).padStart(2, "0");
}}

const labels = {{
    stable: "Lemon DETECTED - STABLE",
    moving: "Lemon MOVING - WATCHING",
    verifying: "VERIFYING WITH GEMMA...",
    eliminated: "Lemon HAS FALLEN!",
    uncertain: "GEMMA UNSURE THIS IS A LEMON",
    starting: "STARTING..."
}};

async function poll() {{

    try {{

        const response = await fetch("/status");
        const data = await response.json();

        camIds.forEach(id => {{

            const cam = data.cameras[id];
            if (!cam) return;

            const statusEl = document.getElementById("status-" + id);
            statusEl.className = "status " + cam.state;
            statusEl.textContent = labels[cam.state] || cam.state;

            document.getElementById("timer-" + id).textContent =
                "Stay time: " + fmt(cam.current_stay_seconds);

            document.getElementById("best-" + id).textContent =
                "Best: " + fmt(cam.best_stay_seconds) +
                "  |  Last: " + fmt(cam.last_stay_seconds) +
                "  |  Falls: " + cam.fall_count;

            document.getElementById("velocity-" + id).textContent =
                "Downward velocity: " + Math.round(cam.velocity) + " px/s";

            document.getElementById("commentary-" + id).textContent =
                cam.commentary ? '"' + cam.commentary + '"' : "";

            const identityEl = document.getElementById("identity-" + id);

            if (cam.identity_commentary) {{
                const tag = cam.identity_result === false
                    ? "Gemma isn't sure this is a lemon: "
                    : "Gemma says: ";
                identityEl.textContent = tag + cam.identity_commentary;
            }} else {{
                identityEl.textContent = "";
            }}
        }});

        const board = data.leaderboard || [];
        const body = document.getElementById("leaderboard-body");
        body.innerHTML = "";

        board.forEach((row, index) => {{
            const tr = document.createElement("tr");
            if (index === 0 && row.best_stay_seconds > 0) {{
                tr.className = "leader";
            }}
            tr.innerHTML =
                "<td>" + row.name + "</td>" +
                "<td>" + fmt(row.best_stay_seconds) + "</td>" +
                "<td>" + fmt(row.last_stay_seconds) + "</td>" +
                "<td>" + row.fall_count + "</td>";
            body.appendChild(tr);
        }});

    }} catch (error) {{
        console.log(error);
    }}
}}

setInterval(poll, 300);

setInterval(() => {{
    camIds.forEach(id => {{
        document.getElementById("frame-" + id).src =
            "/frame/" + id + ".jpg?t=" + Date.now();
    }});
}}, 150);

poll();

</script>

</body>
</html>
"""


@app.route("/")
def index():
    return build_page_html()


@app.route("/status")
def status():

    with web_lock:
        cameras_snapshot = {
            cam_id: dict(data) for cam_id, data in latest_status.items()
        }

    # Build the leaderboard: cameras ranked by their best recorded
    # stay duration, longest first.
    leaderboard = sorted(
        (
            {
                "id": cam_id,
                "name": data["name"],
                "best_stay_seconds": data["best_stay_seconds"],
                "last_stay_seconds": data["last_stay_seconds"],
                "fall_count": data["fall_count"],
            }
            for cam_id, data in cameras_snapshot.items()
        ),
        key=lambda row: row["best_stay_seconds"],
        reverse=True
    )

    return jsonify({
        "cameras": cameras_snapshot,
        "leaderboard": leaderboard
    })


@app.route("/frame/<cam_id>.jpg")
def frame(cam_id):

    with web_lock:
        data = latest_jpeg.get(cam_id)

    if data is None:
        return "", 404

    return Response(data, mimetype="image/jpeg")


def run_web_server():
    app.run(
        host=WEB_HOST,
        port=WEB_PORT,
        threaded=True,
        debug=False,
        use_reloader=False
    )


# ============================================================
# MAIN PROGRAM
# ============================================================

def main():

    if not CAMERAS:
        print("No cameras configured. Add at least one entry to CAMERAS.")
        return

    print("=" * 60)
    print("STARTING LEMON DETECTOR")
    print(f"Cameras: {len(CAMERAS)}")
    print("=" * 60)

    workers = [CameraWorker(cam) for cam in CAMERAS]

    for w in workers:
        w.start()

    threading.Thread(target=run_web_server, daemon=True).start()

    print(f"Website: http://localhost:{WEB_PORT}")

    try:
        while True:
            time.sleep(0.2)

            # If local windows are on, at least one waitKey call per
            # loop keeps the GUI responsive; 'q' on any window quits
            # everything.
            if SHOW_LOCAL_WINDOWS:
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

    except KeyboardInterrupt:
        pass

    finally:
        print("Stopping...")

        for w in workers:
            w.stop()

        for w in workers:
            w.join(timeout=2)

        cv2.destroyAllWindows()


# ============================================================
# START PROGRAM
# ============================================================

if __name__ == "__main__":
    main()
