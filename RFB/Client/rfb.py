import socket
import struct
import hashlib
import time
import threading
from render import Renderer
from inputs import InputHandler

class RFBClient:
    def __init__(self, host, port, password="secret"):
        self.host = host
        self.port = port
        self.password = password.encode('utf-8')
        self.sock = socket.create_connection((host, port))
        self.renderer = Renderer(self)  # Ensure this class has `update_screen`
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

        if not server_version.startswith("RFB 003.003"):
            raise ConnectionError("Unsupported RFB version")

        self.sock.sendall(b"RFB 003.003\n")

    def authenticate(self):
        """Authenticate using password if required."""
        print("🔑 Authenticating...")
        auth_type = self.recv_exact(1)

        if auth_type == b'\x02':  
            self.authenticate_password()
        else:
            raise ConnectionError("❌ Unsupported authentication method")

    def authenticate_password(self):
        """Send hashed password for authentication."""
        print("🔑 Password authentication selected.")
        self.sock.sendall(struct.pack(">B", 2))

        hashed_password = hashlib.md5(self.password).digest()
        print(f"🔄 Sending hashed password: {hashed_password.hex()}")
        self.sock.sendall(hashed_password)

        auth_result = self.recv_exact(1)
        if auth_result == b'\x00':
            print("✅ Authentication successful.")
        else:
            print("❌ Authentication failed.")
            self.sock.close()
            raise ConnectionError("Authentication failed")

    def setup(self):
        """Send the client initialization message."""
        self.sock.sendall(b'\x01')

    def send_key_event(self, keycode, pressed):
        """Send a keyboard event to the server."""
        msg = struct.pack(">BBHI", 4, pressed, 0, keycode)
        self.sock.sendall(msg)

    def send_pointer_event(self, x, y, button_mask):
        """Send a mouse movement/click event."""
        msg = struct.pack(">BBHH", 5, button_mask, x, y)
        self.sock.sendall(msg)

    def receive_framebuffer_update(self):
        """Receive and process framebuffer updates."""
        while self.running:
            try:
                header = self.recv_exact(4)
                if not header:
                    print("❌ Connection closed")
                    break

                msg_type, padding, num_rects = struct.unpack(">BBH", header)

                for _ in range(num_rects):
                    rect_header = self.recv_exact(12)
                    x, y, width, height, encoding = struct.unpack(">HHHHI", rect_header)

                    if encoding == 0:  # Raw encoding
                        pixel_data = self.recv_exact(width * height * 3)
                        self.renderer.update_screen(x, y, width, height, pixel_data)

            except ConnectionError:
                print("❌ Connection lost.")
                self.running = False
                break

    def run(self):
        """Main loop to receive framebuffer updates and handle input."""
        print("✅ Connection successful! Receiving updates...")

        threading.Thread(target=self.input_handler.listen_for_input, daemon=True).start()

        try:
            while self.running:
                self.receive_framebuffer_update()
        except ConnectionError:
            print("❌ Connection closed")
        finally:
            self.renderer.close()  # Close OpenCV window when the connection ends
