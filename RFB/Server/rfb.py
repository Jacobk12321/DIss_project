import socket
import struct
import hashlib
import threading
import time
import pyautogui

class RFBServer:
    def __init__(self, host, port, password="secret"):
        self.host = host
        self.port = port
        self.password = password.encode('utf-8')
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind((self.host, self.port))
        self.sock.listen(1)
        print(f"🔄 Waiting for a connection...")

    def accept_connection(self):
        """Accept a new client connection."""
        self.client_sock, self.client_addr = self.sock.accept()
        print(f"✅ Client connected from {self.client_addr}")

    def perform_handshake(self):
        """Perform the initial RFB handshake."""
        self.client_sock.sendall(b"RFB 003.003\n")
        client_version = self.client_sock.recv(12)
        print(f"🔄 Received client version: {client_version.decode()}")

        if client_version.startswith(b"RFB"):
            self.authenticate_client()
        else:
            print(f"❌ Unsupported client version: {client_version.decode()}")
            self.client_sock.close()

    def authenticate_client(self):
        """Handle authentication with the client."""
        print("🔄 Authentication process started...")
        self.client_sock.sendall(struct.pack(">B", 2))

        auth_type = self.client_sock.recv(1)
        if auth_type == b'\x02':
            self.authenticate_password()
        else:
            print("❌ Unsupported authentication method.")
            self.client_sock.close()

    def authenticate_password(self):
        """Check password from client."""
        print("🔑 Waiting for password authentication...")

        client_hash = self.client_sock.recv(16)
        expected_hash = hashlib.md5(self.password).digest()

        print(f"🔄 Received hash: {client_hash.hex()}")
        print(f"🔄 Expected hash: {expected_hash.hex()}")

        if client_hash == expected_hash:
            print("✅ Authentication successful.")
            self.client_sock.sendall(struct.pack(">B", 0))
        else:
            print("❌ Authentication failed.")
            self.client_sock.sendall(struct.pack(">B", 1))
            self.client_sock.close()

    def capture_screen(self):
        """Capture the screen and send framebuffer updates."""
        try:
            screenshot = pyautogui.screenshot()
            width, height = screenshot.size
            pixels = screenshot.tobytes()

            header = struct.pack(">BBH", 0, 0, 1)
            rect_header = struct.pack(">HHHHI", 0, 0, width, height, 0)

            self.client_sock.sendall(header + rect_header + pixels)

        except BrokenPipeError:
            print("❌ Connection lost during screen capture.")

    def run(self):
        """Run the server."""
        self.accept_connection()
        self.perform_handshake()

        threading.Thread(target=self.capture_screen, daemon=True).start()

        while True:
            try:
                time.sleep(1)
                self.capture_screen()
            except Exception as e:
                print("❌ Server error:", e)
                break

if __name__ == "__main__":
    server = RFBServer("0.0.0.0", 5900, password="secret")
    server.run()
