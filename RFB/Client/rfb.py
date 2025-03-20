import socket
import struct
import hashlib
import threading
import tkinter as tk
from PIL import Image, ImageTk
import numpy as np

PASSWORD = "secret"

class RFBClient:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host, port))

        self.window = tk.Tk()
        self.window.title("Optimized VNC Client")
        self.canvas = tk.Canvas(self.window)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.img = None
        self.img_tk = None

        # Bind events for mouse and keyboard
        self.canvas.bind("<Motion>", self.send_mouse_event)
        self.canvas.bind("<ButtonPress>", self.send_mouse_event)
        self.canvas.bind("<ButtonRelease>", self.send_mouse_event)
        self.window.bind("<KeyPress>", self.send_key_event)
        self.window.bind("<KeyRelease>", self.send_key_event)



    def recv_exact(self, num_bytes):
        """Receive an exact number of bytes from the socket."""
        data = b""
        while len(data) < num_bytes:
            chunk = self.sock.recv(num_bytes - len(data))
            if not chunk:
                raise ConnectionError("Connection closed")
            data += chunk
        return data

    def perform_handshake(self):
        """Perform handshake with server."""
        self.sock.sendall(b"RFB 003.008\n")
        return self.sock.recv(12).decode("utf-8").strip().startswith("RFB 003")

    def authenticate(self):
        """Authenticate with server."""
        if self.recv_exact(1) == b'\x02':
            challenge = self.recv_exact(16)
            hash_response = hashlib.md5(PASSWORD.encode() + challenge).digest()
            self.sock.sendall(hash_response)
            if self.recv_exact(4) != b'\x00\x00\x00\x00':
                raise ConnectionError("Authentication failed")
        else:
            raise ConnectionError("Unsupported authentication method")

    def update_framebuffer(self, x, y, width, height, pixel_data):
        """Update the full desktop, not just a small section."""
        pixels = np.frombuffer(pixel_data, dtype=np.uint8).reshape((height, width, 3))
        new_patch = Image.fromarray(pixels)

        # If first frame, create full-screen image
        if self.img is None:
            screen_width = self.canvas.winfo_screenwidth()
            screen_height = self.canvas.winfo_screenheight()
            self.img = Image.new("RGB", (screen_width, screen_height), "black")

        # Paste only the changed section
        self.img.paste(new_patch, (x, y))

        # Display on canvas
        if self.img_tk is None:
            self.img_tk = ImageTk.PhotoImage(self.img)
            self.canvas.create_image(0, 0, anchor=tk.NW, image=self.img_tk)
        else:
            self.img_tk.paste(self.img)

        self.window.update_idletasks()
        self.window.update()

    def send_mouse_event(self, event):
        """Send mouse movement and button events."""
        button_mask = 1 if event.type == "4" else 0  # Left-click
        msg = struct.pack(">BBHH", 5, button_mask, event.x, event.y)
        self.sock.sendall(msg)

    def send_key_event(self, event):
        """Send keyboard press and release events."""
        down_flag = 1 if event.type == "2" else 0  # KeyPress = "2", KeyRelease = "3"
        keycode = ord(event.char) if event.char else event.keysym_num
        msg = struct.pack(">BBI", 4, down_flag, keycode)
        self.sock.sendall(msg)

    def receive_framebuffer_update(self):
        """Receive and apply framebuffer updates."""
        while True:
            self.recv_exact(1)
            self.recv_exact(1)
            num_rectangles = struct.unpack(">H", self.recv_exact(2))[0]

            for _ in range(num_rectangles):
                x, y, width, height, encoding = struct.unpack(">HHHHI", self.recv_exact(12))
                pixel_data = self.recv_exact(width * height * 3)
                self.update_framebuffer(x, y, width, height, pixel_data)


    def run(self):
        """Run the VNC client."""
        if self.perform_handshake():
            self.authenticate()
            threading.Thread(target=self.receive_framebuffer_update, daemon=True).start()
            self.window.mainloop()
