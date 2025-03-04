import socket
import struct
import hashlib
import time
from PIL import ImageGrab
import os

PASSWORD = "secret"  # The same password as on the client

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
        client_version = self.client_sock.recv(12)
        decoded_version = client_version.decode("utf-8").strip()
        print(f"Received client version: {decoded_version}")
        
        if not decoded_version.startswith("RFB 003"):
            print("Error: Unexpected client version.")
            return False
        
        # Send server version
        self.client_sock.sendall(b"RFB 003.008\n")
        print("Sent server version: RFB 003.008")
        return True

    import os  # Import for random challenge generation

    def authenticate_client(self):
        """Handle VNC authentication."""
        self.client_sock.sendall(b'\x02')  # VNC authentication
        
        # Generate a random challenge
        challenge = os.urandom(16)
        self.client_sock.sendall(challenge)

        # Receive the client's hash response
        received_hash = self.client_sock.recv(16)
        expected_hash = hashlib.md5((PASSWORD.encode() + challenge)).digest()

        if received_hash == expected_hash:
            print("Authentication successful")
            self.client_sock.sendall(b'\x00\x00\x00\x00')  # Auth success
        else:
            print("Authentication failed")
            self.client_sock.sendall(b'\x00\x00\x00\x01')  # Auth failure
            self.client_sock.close()
            return False
        return True


    def capture_screen(self):
        """Capture the screen and send framebuffer updates."""
        while True:
            time.sleep(1/30)  # Reduce CPU usage (30 FPS)
            screen = ImageGrab.grab()  # Take a screenshot
            width, height = screen.size
            pixels = list(screen.getdata())  # Get pixel data as a list of RGB tuples
            
            # Send framebuffer update
            header = struct.pack(">BxH", 0, 1)  # Framebuffer update header
            rect_header = struct.pack(">HHHHI", 0, 0, width, height, 0)  # Rectangle header (no encoding)
            pixel_data = b''.join([struct.pack(">B", c) for pixel in pixels for c in pixel])  # Pack the pixels
            
            try:
                self.client_sock.sendall(header + rect_header + pixel_data)
            except (ConnectionResetError, BrokenPipeError):
                print("Connection closed by client")
                break

    def run(self):
        self.accept_connection()
        if self.perform_handshake():
            if self.authenticate_client():
                self.capture_screen()
