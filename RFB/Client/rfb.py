import socket
import struct
import hashlib
import threading
import time
from render import Renderer
from inputs import InputHandler

PASSWORD = "secret"  # Same as server

class RFBClient:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock = socket.create_connection((host, port))
        self.renderer = Renderer(self)
        self.input_handler = InputHandler(self)
        self.running = True

        self.perform_handshake()
        self.authenticate()
        self.setup()

    def recv_exact(self, num_bytes):
        """Receive an exact number of bytes."""
        data = b""
        while len(data) < num_bytes:
            chunk = self.sock.recv(num_bytes - len(data))
            if not chunk:
                raise ConnectionError("Connection closed")
            data += chunk
        return data

    def perform_handshake(self):
        """Perform the initial RFB handshake."""
        print("🔄 Performing handshake...")
        server_version = self.recv_exact(12).decode()
        print(f"🖥️ Server Version: {server_version}")

        if not server_version.startswith("RFB 003.008"):
            raise ConnectionError("Unsupported RFB version")

        self.sock.sendall(b"RFB 003.008\n")

    def authenticate(self):
        """Handles VNC authentication."""
        auth_type = self.recv_exact(1)
        if auth_type == b'\x02':  # VNC authentication
            challenge = self.recv_exact(16)
            hashed_password = hashlib.md5((PASSWORD + challenge.decode()).encode()).digest()
            self.sock.sendall(hashed_password)

            auth_result = self.recv_exact(4)
            if auth_result != b'\x00\x00\x00\x00':
                raise ConnectionError("Authentication failed")
            print("✅ Authentication successful")
        else:
            raise ConnectionError("Unsupported authentication method")

    def setup(self):
        """Send the client initialization message."""
        self.sock.sendall(b'\x01')  # Request to share the screen

    def receive_framebuffer_update(self):
        """Handle framebuffer updates."""
        while self.running:
            header = self.recv_exact(3)
            if header[0] == 0:  # Framebuffer update
                rect_header = self.recv_exact(12)
                x, y, width, height, encoding = struct.unpack(">HHHHI", rect_header)
                pixel_data = self.recv_exact(width * height * 3)
                self.renderer.update_screen(x, y, width, height, pixel_data)

    def run(self):
        """Main loop to receive framebuffer updates and handle input."""
        print("✅ Connection successful! Receiving updates...")
        threading.Thread(target=self.input_handler.listen_for_input, daemon=True).start()
        self.receive_framebuffer_update()
