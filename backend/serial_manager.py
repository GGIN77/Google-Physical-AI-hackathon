import json
import queue
import threading
import time
from typing import Any, Optional

import serial
from serial import SerialException


class SerialManager:
    """
    Handles communication between the Python backend and ESP32.

    ESP32 -> Python:
        Newline-delimited JSON telemetry

    Python -> ESP32:
        Newline-delimited JSON commands
    """

    def __init__(
        self,
        port: str,
        baudrate: int = 115200,
        timeout: float = 1.0,
    ):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout

        self.serial_connection: Optional[serial.Serial] = None

        self.telemetry_queue: queue.Queue[dict[str, Any]] = queue.Queue()

        self.running = False
        self.connected = False

        self.reader_thread: Optional[threading.Thread] = None

        self.write_lock = threading.Lock()

    # ---------------------------------------------------------
    # Connect
    # ---------------------------------------------------------

    def connect(self) -> bool:
        """
        Open the serial connection and start the background
        telemetry reader.
        """

        if self.connected:
            return True

        try:
            self.serial_connection = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout,
            )

            # Give the ESP32 time to reset after opening serial.
            time.sleep(2)

            self.running = True
            self.connected = True

            self.reader_thread = threading.Thread(
                target=self._reader_loop,
                name="ESP32-Serial-Reader",
                daemon=True,
            )

            self.reader_thread.start()

            return True

        except SerialException:
            self.serial_connection = None
            self.connected = False
            self.running = False

            return False

    # ---------------------------------------------------------
    # Disconnect
    # ---------------------------------------------------------

    def disconnect(self) -> None:
        """
        Stop the reader thread and close the serial connection.
        """

        self.running = False
        self.connected = False

        if self.reader_thread is not None:
            self.reader_thread.join(timeout=1.0)
            self.reader_thread = None

        if self.serial_connection is not None:

            try:
                if self.serial_connection.is_open:
                    self.serial_connection.close()

            except SerialException:
                pass

            self.serial_connection = None

    # ---------------------------------------------------------
    # Background Reader
    # ---------------------------------------------------------

    def _reader_loop(self) -> None:
        """
        Runs in a background daemon thread.

        Reads one line at a time from the ESP32 and converts
        valid JSON messages into Python dictionaries.
        """

        while self.running:

            if (
                self.serial_connection is None
                or not self.serial_connection.is_open
            ):
                time.sleep(0.1)
                continue

            try:

                raw_line = (
                    self.serial_connection.readline()
                )

                if not raw_line:
                    continue

                line = raw_line.decode(
                    "utf-8",
                    errors="replace",
                ).strip()

                if not line:
                    continue

                try:

                    message = json.loads(line)

                except json.JSONDecodeError:
                    # Ignore malformed/non-JSON serial lines.
                    continue

                if isinstance(message, dict):
                    self.telemetry_queue.put(message)

            except SerialException:

                self.connected = False
                self.running = False

                break

            except OSError:

                self.connected = False
                self.running = False

                break

    # ---------------------------------------------------------
    # Send Command
    # ---------------------------------------------------------

    def send_command(
        self,
        command: str,
        **parameters: Any,
    ) -> bool:
        """
        Send a JSON command to the ESP32.

        Example:

            send_command("START")

            send_command(
                "SET_MODE",
                mode="KAMBA_VALI"
            )

            send_command(
                "SERVO",
                angle=90
            )
        """

        if (
            not self.connected
            or self.serial_connection is None
            or not self.serial_connection.is_open
        ):
            return False

        message = {
            "command": command,
            **parameters,
        }

        return self.send_json(message)

    # ---------------------------------------------------------
    # Send JSON
    # ---------------------------------------------------------

    def send_json(
        self,
        message: dict[str, Any],
    ) -> bool:
        """
        Send a dictionary as one newline-delimited JSON message.
        """

        if (
            not self.connected
            or self.serial_connection is None
            or not self.serial_connection.is_open
        ):
            return False

        try:

            payload = (
                json.dumps(
                    message,
                    separators=(",", ":"),
                )
                + "\n"
            )

            with self.write_lock:

                self.serial_connection.write(
                    payload.encode("utf-8")
                )

                self.serial_connection.flush()

            return True

        except (
            SerialException,
            OSError,
        ):

            self.connected = False

            return False

    # ---------------------------------------------------------
    # Get One Telemetry Message
    # ---------------------------------------------------------

    def get_message(
        self,
        timeout: float = 0.0,
    ) -> Optional[dict[str, Any]]:
        """
        Retrieve one telemetry message.

        timeout=0 means non-blocking.
        """

        try:

            return self.telemetry_queue.get(
                timeout=timeout
            )

        except queue.Empty:

            return None

    # ---------------------------------------------------------
    # Get All Available Messages
    # ---------------------------------------------------------

    def get_messages(
        self,
        max_messages: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Retrieve all currently available telemetry messages,
        up to max_messages.
        """

        messages: list[dict[str, Any]] = []

        for _ in range(max_messages):

            try:

                message = (
                    self.telemetry_queue.get_nowait()
                )

            except queue.Empty:

                break

            messages.append(message)

        return messages

    # ---------------------------------------------------------
    # Clear Telemetry Queue
    # ---------------------------------------------------------

    def clear_queue(self) -> None:
        """
        Remove all unread telemetry messages.
        """

        while True:

            try:

                self.telemetry_queue.get_nowait()

            except queue.Empty:

                break

    # ---------------------------------------------------------
    # Connection Status
    # ---------------------------------------------------------

    def is_connected(self) -> bool:
        """
        Return the current serial connection status.
        """

        return (
            self.connected
            and self.serial_connection is not None
            and self.serial_connection.is_open
        )

    # ---------------------------------------------------------
    # Context Manager Support
    # ---------------------------------------------------------

    def __enter__(self):
        """
        Allows:

            with SerialManager("COM5") as serial_manager:
                ...
        """

        self.connect()

        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ):
        """
        Automatically disconnect when leaving the context.
        """

        self.disconnect()