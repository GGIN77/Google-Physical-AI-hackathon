import serial
import json
import queue
import threading
import time

class SerialManager:
    def __init__(self):
        self.ser = None
        self.queue = queue.Queue()
        self.running = False
        self.thread = None

    def connect(self, port, baudrate=115200):
        try:
            self.ser = serial.Serial(port, baudrate, timeout=1)
            self.running = True
            self.thread = threading.Thread(target=self._read_loop, daemon=True)
            self.thread.start()
            return True
        except Exception as e:
            print(f"Serial Connection Error: {e}")
            return False

    def _read_loop(self):
        while self.running and self.ser and self.ser.is_open:
            try:
                if self.ser.in_waiting > 0:
                    line = self.ser.readline().decode('utf-8').strip()
                    if line:
                        try:
                            data = json.loads(line)
                            self.queue.put(data)
                        except json.JSONDecodeError:
                            pass
            except Exception as e:
                print(f"Read error: {e}")
                break
            time.sleep(0.01)

    def send(self, command_str):
        if self.ser and self.ser.is_open:
            self.ser.write(command_str.encode('utf-8'))

    def read_queue(self):
        items = []
        while not self.queue.empty():
            items.append(self.queue.get())
        return items

    def disconnect(self):
        self.running = False
        if self.ser and self.ser.is_open:
            self.ser.close()