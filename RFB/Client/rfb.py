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
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host, port))

        # Tkinter setup
        self.window = tk.Tk()
        self.window.title("VNC Client")
        self.canvas = tk.Canvas(self.window)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.img_tk = None
        self.img = None

        # Bind input events
        self.canvas.bind("<Motion>", self.send_mouse_event)
        self.canvas.bind("<ButtonPress>", self.send_mouse_event)
        self.canvas.bind("<ButtonRelease>", self.send_mouse_event)
        self.window.bind("<KeyPress>", self.send_key_event)
        self.window.bind("<KeyRelease>", self.send_key_event)

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
        self.sock.sendall(b"RFB 003.008\n")
        server_version = self.sock.recv(12).decode("utf-8").strip()
        print(f"Received server version: {server_version}")
        return server_version.startswith("RFB 003")

    def authenticate(self):
        """Handle VNC authentication."""
        auth_type = self.recv_exact(1)
        if auth_type == b'\x02':
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
        self.sock.sendall(b'\x01')

    def update_framebuffer(self, width, height, pixel_data):
        """Efficiently update the framebuffer without flickering."""
        pixels = np.frombuffer(pixel_data, dtype=np.uint8).reshape((height, width, 3))
        self.img = Image.fromarray(pixels)

        if self.img_tk is None:
            self.img_tk = ImageTk.PhotoImage(self.img)
            self.canvas.create_image(0, 0, anchor=tk.NW, image=self.img_tk)
        else:
            self.img_tk.paste(self.img)

        self.window.update()


    def receive_framebuffer_update(self):
        """Receive and display framebuffer updates."""
        try:
            while True:
                self.recv_exact(1)  # Message type
                self.recv_exact(1)  # Padding
                num_rectangles = struct.unpack(">H", self.recv_exact(2))[0]

                for _ in range(num_rectangles):
                    x, y, width, height, encoding = struct.unpack(">HHHHI", self.recv_exact(12))
                    pixel_data = self.recv_exact(width * height * 3)
                    self.update_framebuffer(width, height, pixel_data)

        except Exception as e:
            print(f"Error receiving framebuffer update: {e}")

    def send_mouse_event(self, event):
        """Send mouse movement and button events."""
        button_mask = 0
        if event.type == tk.EventType.ButtonPress:
            button_mask = event.num
        elif event.type == tk.EventType.ButtonRelease:
            button_mask = 0

        msg = struct.pack(">BBHH", 5, button_mask, event.x, event.y)
        self.sock.sendall(msg)

    def send_key_event(self, event):
        """Send keyboard press and release events."""
        down_flag = 1 if event.type == tk.EventType.KeyPress else 0
        keycode = ord(event.char) if event.char else event.keysym_num
        msg = struct.pack(">BBI", 4, down_flag, keycode)
        self.sock.sendall(msg)

    def run(self):
        """Start the client."""
        if self.perform_handshake():
            self.authenticate()
            self.setup()
            threading.Thread(target=self.receive_framebuffer_update, daemon=True).start()
            self.window.mainloop()
