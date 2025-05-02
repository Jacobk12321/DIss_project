from PIL import Image
import time
import socket
import struct
from Crypto.Cipher import DES
import threading

from inputs import InputHandler
from render import Renderer

PASSWORD = "secret"

def des_key_from_password(password):
    key = password.ljust(8, '\x00')[:8]  # Pad or trim to 8 bytes
    # Bit-reverse each byte
    return bytes([int('{:08b}'.format(b)[::-1], 2) for b in key.encode("latin-1")])

class RFBClient:
    def __init__(self, host, port):
        self.sock = socket.create_connection((host, port))
        self.input_handler = InputHandler(self.sock)
        self.renderer = Renderer(
            on_key=self.handle_key,
            on_mouse=self.handle_mouse
        )
        self.screen_image = None
        self.last_update_time = time.time()
        self.update_threshold = 1 / 30  # Cap updates at 30 FPS

    def recv_exact(self, n):
        data = b""
        while len(data) < n:
            chunk = self.sock.recv(n - len(data))
            if not chunk:
                raise ConnectionError("Connection closed")
            data += chunk
        return data

    def perform_handshake(self):
        self.sock.sendall(b"RFB 003.008\n")
        return self.sock.recv(12).startswith(b"RFB 003")

    def authenticate(self):
        if self.recv_exact(1) == b'\x02': # VNC auth
            challenge = self.recv_exact(16)
            des_key = des_key_from_password(PASSWORD)
            des = DES.new(des_key, DES.MODE_ECB)
            response = des.encrypt(challenge[:8]) + des.encrypt(challenge[8:])
            self.sock.sendall(response)

            if self.recv_exact(4) != b'\x00\x00\x00\x00':
                raise ConnectionError("Authentication failed")

    def handle_key(self, event):
        self.input_handler.send_key_event(event.type, event.keysym, event.char, event.keycode)

    def handle_mouse(self, event):
        self.input_handler.send_mouse_event(event.type, event.x, event.y, getattr(event, 'num', 0))

    def update_framebuffer(self, x, y, w, h, pixel_data):
        patch = Image.frombuffer("RGB", (w, h), pixel_data)

        if self.screen_image is None:
            self.screen_image = Image.new("RGB", (w, h))

        if x + w > self.screen_image.width or y + h > self.screen_image.height:
            new_width = max(self.screen_image.width, x + w)
            new_height = max(self.screen_image.height, y + h)
            new_img = Image.new("RGB", (new_width, new_height))
            new_img.paste(self.screen_image, (0, 0))
            self.screen_image = new_img

        self.screen_image.paste(patch, (x, y))

    def receive_updates(self): # screen updates
        while True:
            try:
                msg_type = self.recv_exact(1)
                if not msg_type:
                    print("Connection closed by server")
                    break

                self.recv_exact(1)
                num_rects = struct.unpack(">H", self.recv_exact(2))[0]

                any_updated = False
                for _ in range(num_rects):
                    x, y, w, h, encoding = struct.unpack(">HHHHI", self.recv_exact(12))
                    if encoding != 0:
                        print(f"Unsupported encoding: {encoding}")
                        continue

                    pixel_data = self.recv_exact(w * h * 3)
                    self.update_framebuffer(x, y, w, h, pixel_data)
                    any_updated = True

                now = time.time()
                if any_updated and now - self.last_update_time >= self.update_threshold:
                    self.renderer.update_image(self.screen_image)
                    self.last_update_time = now

            except (ConnectionError, struct.error) as e:
                print(f"Error receiving updates: {e}")
                break

    def run(self):
        if not self.perform_handshake():
            print("Handshake failed")
            return

        self.authenticate()
        print("Connected and authenticated to VNC server")

        threading.Thread(target=self.receive_updates, daemon=True).start()
        self.renderer.start_loop()
