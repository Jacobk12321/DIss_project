import socket
import struct
import hashlib
import time
from PIL import ImageGrab  # Use ImageGrab instead of pyautogui for Linux support

PASSWORD = "secret"  # Change this password

class RFBServer:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind((self.host, self.port))
        self.sock.listen(1)
        print(f"🔄 Waiting for a connection...")

    def accept_connection(self):
        self.client_sock, self.client_addr = self.sock.accept()
        print(f"✅ Client connected from {self.client_addr}")

    def perform_handshake(self):
        """Handle RFB 3.8 handshake"""
        server_version = b"RFB 003.008\n"
        self.client_sock.sendall(server_version)

        client_version = self.client_sock.recv(12)
        print(f"🔄 Received client version: {client_version.decode().strip()}")

        if not client_version.startswith(b"RFB 003.008"):
            print("❌ Unsupported RFB version")
            self.client_sock.close()
            return False

        self.authenticate_client()
        return True

    def authenticate_client(self):
        """Handles VNC authentication"""
        self.client_sock.sendall(b'\x02')  # VNC authentication

        challenge = b"1234567890123456"  # Fake challenge for simplicity
        self.client_sock.sendall(challenge)

        received_hash = self.client_sock.recv(16)
        expected_hash = hashlib.md5((PASSWORD + challenge.decode()).encode()).digest()

        if received_hash == expected_hash:
            print("✅ Authentication successful")
            self.client_sock.sendall(b'\x00\x00\x00\x00')  # Auth success
        else:
            print("❌ Authentication failed")
            self.client_sock.sendall(b'\x00\x00\x00\x01')  # Auth failed
            self.client_sock.close()

    def capture_screen(self):
        """Capture screen and send framebuffer updates"""
        while True:
            time.sleep(0.1)  # Reduce CPU usage
            screen = ImageGrab.grab()  # Take a screenshot
            width, height = screen.size
            pixels = screen.tobytes()

            header = struct.pack(">BxH", 0, 1)  # Framebuffer update
            rect_header = struct.pack(">HHHHI", 0, 0, width, height, 0)  # Raw encoding

            try:
                self.client_sock.sendall(header + rect_header + pixels)
            except (ConnectionResetError, BrokenPipeError):
                print("❌ Connection closed by client")
                break

    def run(self):
        self.accept_connection()
        if self.perform_handshake():
            self.capture_screen()

if __name__ == "__main__":
    server = RFBServer("0.0.0.0", 5900)
    server.run()
