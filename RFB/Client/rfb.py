import time
import socket
import struct
import hashlib
import threading
from PIL import Image
import numpy as np

from inputs import InputHandler
from render import Renderer

PASSWORD = "secret"

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

    def recv_exact(self, n):
        """Helper function to receive an exact number of bytes from the socket."""
        data = b""
        while len(data) < n:
            chunk = self.sock.recv(n - len(data))
            if not chunk:
                raise ConnectionError("Connection closed")
            data += chunk
        return data

    def perform_handshake(self):
        """Perform RFB protocol handshake."""
        self.sock.sendall(b"RFB 003.008\n")
        return self.sock.recv(12).startswith(b"RFB 003")

    def authenticate(self):
        """Authenticate with the server using the password."""
        if self.recv_exact(1) == b'\x02':
            challenge = self.recv_exact(16)
            response = hashlib.md5(PASSWORD.encode() + challenge).digest()
            self.sock.sendall(response)
            if self.recv_exact(4) != b'\x00\x00\x00\x00':
                raise ConnectionError("Authentication failed")

    def handle_key(self, event):
        """Handle keyboard events and forward them to the input handler."""
        self.input_handler.send_key_event(event.type, event.keysym, event.char, event.keycode)

    def handle_mouse(self, event):
        """Handle mouse events and forward them to the input handler."""
        self.input_handler.send_mouse_event(event.type, event.x, event.y, getattr(event, 'num', 0))

    def update_framebuffer(self, x, y, w, h, pixel_data):
        """Update the framebuffer with new pixel data."""
        patch = Image.fromarray(np.frombuffer(pixel_data, dtype=np.uint8).reshape((h, w, 3)))

        # Only update if there's a change
        if self.screen_image is None:
            self.screen_image = Image.new("RGB", (w, h))

        # Check if the framebuffer needs an update
        existing_patch = self.screen_image.crop((x, y, x + w, y + h))
        if existing_patch != patch:
            self.screen_image.paste(patch, (x, y))
            self.renderer.update_image(self.screen_image)

    def receive_updates(self):
        """Receive updates from the server and handle framebuffer updates."""
        while True:
            current_time = time.time()

            # Throttle updates to avoid too many updates per second
            if current_time - self.last_update_time < 1/30:
                time.sleep(0.01)  # Sleep for 10ms, avoiding too frequent processing
            
            # Receive the next update packet
            self.recv_exact(1)  # Skip the message type byte
            self.recv_exact(1)  # Skip padding byte
            num_rects = struct.unpack(">H", self.recv_exact(2))[0]

            for _ in range(num_rects):
                # Read the rectangle header (x, y, width, height, encoding)
                x, y, w, h, encoding = struct.unpack(">HHHHI", self.recv_exact(12))
                pixel_data = self.recv_exact(w * h * 3)  # Read pixel data
                self.update_framebuffer(x, y, w, h, pixel_data)

            # Update the time of the last update received
            self.last_update_time = current_time

    def run(self):
        """Run the RFB client."""
        self.perform_handshake()
        self.authenticate()
        threading.Thread(target=self.receive_updates, daemon=True).start()
        self.renderer.start_loop()
