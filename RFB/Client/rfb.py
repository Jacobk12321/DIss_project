import socket
import struct
import hashlib
import threading
import numpy as np
import tkinter as tk
from PIL import Image, ImageTk
from io import BytesIO

PASSWORD = "secret"  # Same as server

class RFBClient:
    def __init__(self, host, port):
        """Initialize the RFB client connection."""
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host, port))

        # Set up the Tkinter window for displaying the framebuffer
        self.window = tk.Tk()
        self.window.title("VNC Client")
        self.canvas = tk.Canvas(self.window)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.img_tk = None
        self.img = None

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
        """Perform the initial handshake with the server."""
        # Send RFB 3.8 handshake
        handshake_message = b"RFB 003.008\n"
        self.sock.sendall(handshake_message)

        # Receive server version
        server_version = self.sock.recv(12)
        decoded_version = server_version.decode("utf-8").strip()
        print(f"Received server version: {decoded_version}")
        if not decoded_version.startswith("RFB 003"):
            print("Error: Unexpected server version.")
            return False

        return True

    def authenticate(self):
        """Handle VNC authentication."""
        auth_type = self.recv_exact(1)
        if auth_type == b'\x02':  # VNC Authentication
            challenge = self.recv_exact(16)
            hash_response = hashlib.md5((PASSWORD.encode() + challenge)).digest()
            self.sock.sendall(hash_response)
            response = self.recv_exact(4)
            if response != b'\x00\x00\x00\x00':
                raise ConnectionError("Authentication failed")
            print("Authentication successful")
        else:
            raise ConnectionError("Unsupported authentication method")

    def setup(self):
        """Send the client initialization message."""
        self.sock.sendall(b'\x01')  # Request to share the screen

    def update_framebuffer(self, width, height, pixel_data):
        """Update the framebuffer and show on Tkinter canvas."""
        # Convert raw pixel data to numpy array
        pixels = np.frombuffer(pixel_data, dtype=np.uint8).reshape((height, width, 3))

        # Create Image from numpy array
        self.img = Image.fromarray(pixels)
        
        # Create a PhotoImage for Tkinter
        self.img_tk = ImageTk.PhotoImage(self.img)

        # Update canvas image
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.img_tk)
        self.window.update_idletasks()
        self.window.update()

    def receive_framebuffer_update(self):
        """Receive and display framebuffer updates in real-time."""
        try:
            while True:
                # Framebuffer update header
                self.recv_exact(1)  # message type
                self.recv_exact(1)  # padding
                num_rectangles = struct.unpack(">H", self.recv_exact(2))[0]
                
                for _ in range(num_rectangles):
                    # Rectangle header (x, y, width, height, encoding)
                    x, y, width, height, encoding = struct.unpack(">HHHHI", self.recv_exact(12))
                    
                    # Read the pixel data (RGB format)
                    pixel_data = self.recv_exact(width * height * 3)

                    # Update the framebuffer in Tkinter
                    self.update_framebuffer(width, height, pixel_data)

        except Exception as e:
            print(f"Error receiving framebuffer update: {e}")

    def run(self):
        """Start the client."""
        if self.perform_handshake():
            self.authenticate()
            self.setup()

            # Start receiving updates in a separate thread
            threading.Thread(target=self.receive_framebuffer_update, daemon=True).start()

            # Run Tkinter main loop
            self.window.mainloop()
