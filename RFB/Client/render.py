import struct
from PIL import Image
import numpy as np
import cv2

class Renderer:
    def __init__(self, client):
        self.client = client
        self.window_name = "RFB Viewer"

        # Create a named window that can be resized
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)

    def update_screen(self, x, y, width, height, pixel_data):
        """Update the screen dynamically with new framebuffer data."""
        print(f"🖥️ Updating screen at ({x}, {y}) with size {width}x{height}")

        # Convert raw pixel data to an image
        image = Image.frombytes("RGB", (width, height), pixel_data)

        # Convert PIL image to OpenCV format (numpy array)
        frame = np.array(image)
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)  # Convert RGB to BGR for OpenCV

        # Display the frame
        cv2.imshow(self.window_name, frame)

        # Wait briefly and process any window events
        cv2.waitKey(1)  # Use a small delay to allow window updates

    def close(self):
        """Close the OpenCV window properly when exiting."""
        cv2.destroyAllWindows

        
    def handle_framebuffer_update(self):
        """Handle framebuffer updates from the server."""
        print("🔍 Waiting for framebuffer update...")

        try:
            header = self.client.recv_exact(10)
            msg_type, _, num_rects = struct.unpack(">BBH", header)

            if msg_type == 0:  # Framebuffer update
                for _ in range(num_rects):
                    rect_header = self.client.recv_exact(12)
                    x, y, width, height, encoding = struct.unpack(">HHHHI", rect_header)
                    print(f"📸 Framebuffer Update: ({x},{y}) {width}x{height}, Encoding: {encoding}")

                    if encoding == 0:  # Raw encoding
                        pixel_data = self.client.recv_exact(width * height * 3)
                        print(f"🖼️ Received {len(pixel_data)} bytes of raw pixel data")
            else:
                print(f"⚠️ Unexpected message type: {msg_type}")

        except ConnectionError:
            print("❌ Connection closed while waiting for framebuffer update")
