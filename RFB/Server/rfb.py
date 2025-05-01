import socket
import struct
from Crypto.Cipher import DES
import time
import os
import pyautogui
import threading
from framebuffer import FrameBuffer
from input_handler import InputHandler

PASSWORD = "secret"


def des_key_from_password(password):
    key = password.ljust(8, '\x00')[:8]  # Pad or trim
    return bytes([int('{:08b}'.format(b)[::-1], 2) for b in key.encode("latin-1")])

class RFBServer:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind((self.host, self.port))
        self.sock.listen(1)
        print(f"Waiting for a connection...")

        self.input_handler = InputHandler()
        self.framebuffer = FrameBuffer(1920, 1080)  # screen size 

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

        response = self.client_sock.recv(16)
        des_key = des_key_from_password(PASSWORD)
        des = DES.new(des_key, DES.MODE_ECB)
        expected = des.encrypt(challenge[:8]) + des.encrypt(challenge[8:])

        if response == expected:
            print("Authentication successful")
            self.client_sock.sendall(b'\x00\x00\x00\x00')
            return True
        else:
            print("Authentication failed")
            self.client_sock.sendall(b'\x00\x00\x00\x01')
            self.client_sock.close()
            return False


    def handle_client_inputs(self):
        while True:
            msg_type = self.client_sock.recv(1)
            if not msg_type:
                break

            if msg_type == b'\x04':  # Key event
                recv_time = time.time()
                down_flag, keycode = struct.unpack(">BI", self.client_sock.recv(5))

                key = chr(keycode) if keycode < 256 else f"Keycode {keycode}"
                action = "Pressed" if down_flag else "Released"
                print(f"[Server] Key {action}: {key} | Received at {recv_time:.6f}")

                if down_flag:
                    pyautogui.keyDown(key)
                else:
                    pyautogui.keyUp(key)

                self.input_handler.handle_key_event(keycode, down_flag == 1)

            elif msg_type == b'\x05':  # Mouse event
                recv_time = time.time()
                button_mask, x, y = struct.unpack(">BHH", self.client_sock.recv(5))

                # Determine which mouse button
                button_name = "Unknown"
                if button_mask == 1:
                    button_name = "Left"
                elif button_mask == 2:
                    button_name = "Middle"
                elif button_mask == 4:
                    button_name = "Right"

                print(f"[Server] Mouse Event Received at {recv_time:.6f} - Button: {button_name}, Position: ({x}, {y})")

                pyautogui.moveTo(x, y, duration=0, _pause=False)
                if button_mask:
                    pyautogui.click()

                self.input_handler.handle_mouse_event(x, y, button_mask)
    def run(self):
        self.accept_connection()
        if self.perform_handshake() and self.authenticate_client():
            threading.Thread(target=self.handle_client_inputs, daemon=True).start()
            self.framebuffer.stream_updates(self.client_sock)