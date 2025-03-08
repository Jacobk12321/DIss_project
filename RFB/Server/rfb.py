import socket
import struct
import hashlib
import time
import os
import pyautogui
from PIL import ImageGrab
import threading

PASSWORD = "secret"

class RFBServer:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind((self.host, self.port))
        self.sock.listen(1)
        print(f"Waiting for a connection...")

    def accept_connection(self):
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
        self.client_sock.sendall(b'\x02')
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
        """Capture and send screen updates."""
        while True:
            time.sleep(1/30)
            screen = ImageGrab.grab()
            width, height = screen.size
            pixels = list(screen.getdata())

            header = struct.pack(">BxH", 0, 1)
            rect_header = struct.pack(">HHHHI", 0, 0, width, height, 0)
            pixel_data = b''.join([struct.pack(">B", c) for pixel in pixels for c in pixel])

            try:
                self.client_sock.sendall(header + rect_header + pixel_data)
            except (ConnectionResetError, BrokenPipeError):
                print("Connection closed by client")
                break

    def handle_client_inputs(self):
        """Receive and process mouse/keyboard inputs."""
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
        self.accept_connection()
        if self.perform_handshake() and self.authenticate_client():
            threading.Thread(target=self.handle_client_inputs, daemon=True).start()
            self.capture_screen()
