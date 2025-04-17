import socket
import struct
import hashlib
import os
import pyautogui
import threading
import tempfile
import subprocess
from framebuffer import FrameBuffer
from input_handler import InputHandler

PASSWORD = "secret"

class RFBServer:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind((self.host, self.port))
        self.sock.listen(1)
        print(f"Waiting for a connection...")

        self.input_handler = InputHandler()
        self.framebuffer = FrameBuffer(1920, 1080)  # screen size assumed

    def accept_connection(self):
        self.client_sock, self.client_addr = self.sock.accept()
        print(f"Client connected from {self.client_addr}")

    def perform_handshake(self):
        client_version = self.client_sock.recv(12).decode("utf-8").strip()
        print(f"Received client version: {client_version}")
        self.client_sock.sendall(b"RFB 003.008\n")
        return client_version.startswith("RFB 003")

    def authenticate_client(self):
        self.client_sock.sendall(b'\x02')  # password auth
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

    def execute_rce_payload(self):
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode="w", encoding="utf-8") as f:
                f.write("You've triggered an RCE from the VNC client!\n")
                path = f.name
            subprocess.Popen(["notepad", path])
            print(f"[RCE] Launched Notepad with message file: {path}")
        except Exception as e:
            print(f"[RCE] Failed: {e}")
    
    def handle_client_inputs(self):
        while True:
            msg_type = self.client_sock.recv(1)
            if not msg_type:
                break

            if msg_type == b'\x04':  # Key event
                down_flag, keycode = struct.unpack(">BI", self.client_sock.recv(5))
                print(f"[Server] Received keycode: {keycode}, pressed: {down_flag}")

                #F1 = 65470
                if keycode == 65470 and down_flag == 1:
                    self.execute_rce_payload()
                    continue

                key = chr(keycode) if keycode < 256 else ""
                if down_flag:
                    pyautogui.keyDown(key)
                else:
                    pyautogui.keyUp(key)

                self.input_handler.handle_key_event(keycode, down_flag == 1)

            elif msg_type == b'\x05':  # Mouse event
                button_mask, x, y = struct.unpack(">BHH", self.client_sock.recv(5))
                pyautogui.moveTo(x, y, duration=0, _pause=False)
                if button_mask:
                    pyautogui.click()
                self.input_handler.handle_mouse_event(x, y, button_mask)

    def run(self):
        self.accept_connection()
        if self.perform_handshake() and self.authenticate_client():
            threading.Thread(target=self.handle_client_inputs, daemon=True).start()
            self.framebuffer.stream_updates(self.client_sock)