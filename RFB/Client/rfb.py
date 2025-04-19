import time
import socket
import struct
import hashlib
import threading
from PIL import Image

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
        self.update_threshold = 1/60  #60fps

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
        # Create array from pixel data
        patch = Image.frombuffer("RGB", (w, h), pixel_data)

        # Initialize screen image
        if self.screen_image is None:
            self.screen_image = Image.new("RGB", (w, h))
        
        # Ensure screen image is large enough 
        if x + w > self.screen_image.width or y + h > self.screen_image.height:
            new_width = max(self.screen_image.width, x + w)
            new_height = max(self.screen_image.height, y + h)
            new_img = Image.new("RGB", (new_width, new_height))
            new_img.paste(self.screen_image, (0, 0))
            self.screen_image = new_img

        # Apply the patch to our local framebuffer
        self.screen_image.paste(patch, (x, y))
        
        # Rate-limited rendering to prevent flashing
        current_time = time.time()
        if current_time - self.last_update_time >= self.update_threshold:
            self.renderer.update_image(self.screen_image)
            self.last_update_time = current_time

    def receive_updates(self):
        """Receive updates from the server and handle framebuffer updates."""
        while True:
            try:
                # Receive the message type byte
                msg_type = self.recv_exact(1)
                
                if not msg_type:
                    print("Connection closed by server")
                    break
                    
                # Skip padding byte
                self.recv_exact(1)
                
                # Number of rectangles
                num_rects = struct.unpack(">H", self.recv_exact(2))[0]
                
                # Process all rectangles when updating
                updates_in_batch = False
                for _ in range(num_rects):
                    # Rectangle header (x, y, width, height, encoding)
                    x, y, w, h, encoding = struct.unpack(">HHHHI", self.recv_exact(12))
                    
                    # Only support raw encoding (0)
                    if encoding != 0:
                        print(f"Unsupported encoding: {encoding}")
                        continue
                        
                    # Read pixel data -  w*h*3 bytes (RGB)
                    pixel_data = self.recv_exact(w * h * 3)
                    
                    # Update framebuffer
                    self.update_framebuffer(x, y, w, h, pixel_data)
                    updates_in_batch = True
                
                #  Render after rectangles are processed
                if updates_in_batch:
                    self.renderer.update_image(self.screen_image)
                    self.last_update_time = time.time()
                    
            except (ConnectionError, struct.error) as e:
                print(f"Error receiving updates: {e}")
                break

    def run(self):
        """Run the RFB client."""
        if not self.perform_handshake():
            print("Handshake failed")
            return
            
        self.authenticate()
        print("Connected and authenticated to VNC server")
        
        # Start update thread
        threading.Thread(target=self.receive_updates, daemon=True).start()
        
        # Start UI main loop
        self.renderer.start_loop()