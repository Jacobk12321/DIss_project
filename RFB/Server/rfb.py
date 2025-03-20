import socket
import struct
import hashlib
import time
import os
import pyautogui
from PIL import ImageGrab, ImageChops , Image
import threading
import mss
import numpy as np

PASSWORD = "secret"

class RFBServer:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind((self.host, self.port))
        self.sock.listen(1)
        print(f"Waiting for a connection...")

        self.previous_frame = None  # Store the last screen capture

    def accept_connection(self):
        """Wait for a client to connect."""
        self.client_sock, self.client_addr = self.sock.accept()
        print(f"Client connected from {self.client_addr}")

    def perform_handshake(self):
        """Perform the initial handshake with the client."""
        client_version = self.client_sock.recv(12).decode("utf-8").strip()
        print(f"Received client version: {client_version}")
        self.client_sock.sendall(b"RFB 003.008\n")
        return client_version.startswith("RFB 003")

    def authenticate_client(self):
        """Handle VNC authentication."""
        self.client_sock.sendall(b'\x02')  # Only support password auth
        challenge = os.urandom(16)
        self.client_sock.sendall(challenge)

        received_hash = self.client_sock.recv(16)
        expected_hash = hashlib.md5((PASSWORD.encode() + challenge)).digest()

        if received_hash == expected_hash:
            print("Authentication successful")
            self.client_sock.sendall(b'\x00\x00\x00\x00')
            return True
        else:
            print("Authentication failed")
            self.client_sock.sendall(b'\x00\x00\x00\x01')
            self.client_sock.close()
            return False

    def capture_screen(self):
        """Capture the entire desktop across all monitors and send only changed areas."""
        with mss.mss() as sct:
            previous_frame = None  # Store the previous screen for comparison

            while True:
                time.sleep(1 / 30)  # Capture at ~30 FPS

                # Get the full desktop (all monitors)
                screenshot = sct.grab(sct.monitors[0])  
                img = Image.frombytes("RGB", (screenshot.width, screenshot.height), screenshot.rgb)

                if previous_frame is None:
                    # First frame: Send the entire desktop
                    diff_image = img  
                else:
                    # Get only the changed areas
                    diff_image = ImageChops.difference(img, previous_frame)

                previous_frame = img  # Store the current frame for next iteration

                # Get bounding box of changed area
                bbox = diff_image.getbbox()
                if bbox:
                    x, y, w, h = bbox[0], bbox[1], bbox[2] - bbox[0], bbox[3] - bbox[1]
                    changed_pixels = img.crop((x, y, x + w, y + h))

                    pixel_data = changed_pixels.tobytes()

                    # Send update
                    try:
                        self.client_sock.sendall(struct.pack(">BxH", 0, 1))  # Framebuffer update header
                        self.client_sock.sendall(struct.pack(">HHHHI", x, y, w, h, 0))  # Rectangle header
                        self.client_sock.sendall(pixel_data)  # Image data
                    except (ConnectionResetError, BrokenPipeError):
                        print("Client disconnected.")
                        break

    def handle_client_inputs(self):
        """Receive and process mouse/keyboard inputs from the client."""
        while True:
            msg_type = self.client_sock.recv(1)
            if not msg_type:
                break

            if msg_type == b'\x05':  # Mouse event
                button_mask, x, y = struct.unpack(">BHH", self.client_sock.recv(5))
                pyautogui.moveTo(x, y, duration=0, _pause=False)
                if button_mask:
                    pyautogui.click()

            elif msg_type == b'\x04':  # Keyboard event
                down_flag, keycode = struct.unpack(">BI", self.client_sock.recv(5))
                key = chr(keycode) if keycode < 256 else ""
                if down_flag:
                    pyautogui.keyDown(key)
                else:
                    pyautogui.keyUp(key)

    def run(self):
        """Start the server."""
        self.accept_connection()
        if self.perform_handshake() and self.authenticate_client():
            threading.Thread(target=self.handle_client_inputs, daemon=True).start()
            self.capture_screen()