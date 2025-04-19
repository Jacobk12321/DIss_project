import time
import struct
from PIL import ImageChops, Image
import mss

class FrameBuffer:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.previous_frame = None
        self.frame_interval = 1/30  # 30 FPS
        self.last_frame_time = 0
        self.min_pixel_threshold = 500  # Minimum number of changed pixels to trigger update

    def significant_change(self, diff_img, pixel_threshold=None):
        if pixel_threshold is None:
            pixel_threshold = self.min_pixel_threshold
            
        # Count changed pixels
        diff_data = diff_img.getdata()
        changed_pixels = sum(1 for pixel in diff_data if pixel != (0, 0, 0))
        return changed_pixels > pixel_threshold

    def stream_updates(self, client_sock):
        with mss.mss() as sct:
            monitor = sct.monitors[0]  # Get the main monitor
            
            # Send full frame initially
            screenshot = sct.grab(monitor)
            img = Image.frombytes("RGB", (screenshot.width, screenshot.height), screenshot.rgb)
            self.previous_frame = img.copy()
            self.send_full_frame(img, client_sock)
            
            # Update timing
            self.last_frame_time = time.time()
            
            while True:
                # Calculate time to next frame
                current_time = time.time()
                elapsed = current_time - self.last_frame_time
                
                # If time is too close to nex update then wait 
                if elapsed < self.frame_interval:
                    time.sleep(max(0.001, self.frame_interval - elapsed))
                    continue
                
                # Take screenshot
                try:
                    screenshot = sct.grab(monitor)
                    img = Image.frombytes("RGB", (screenshot.width, screenshot.height), screenshot.rgb)
                    
                    # Compute image difference
                    diff_image = ImageChops.difference(img, self.previous_frame)
                    
                    # Check if there's a significant change
                    bbox = diff_image.getbbox()
                    if bbox and self.significant_change(diff_image.crop(bbox)):
                        # Save the current frame and update timestamp
                        self.previous_frame = img.copy()
                        self.last_frame_time = time.time()
                        
                        # Send changed portion
                        self.send_diff(img, bbox, client_sock)
                    else:
                        # No significant change, just update the timestamp
                        self.last_frame_time = time.time()
                        
                except (ConnectionResetError, BrokenPipeError) as e:
                    print(f"Client disconnected: {e}")
                    break
                except Exception as e:
                    print(f"Error capturing screen: {e}")
                    time.sleep(0.5) 

    def send_full_frame(self, img, client_sock):
        x, y = 0, 0
        w, h = img.size
        pixel_data = img.tobytes()

        try:
            # Send framebuffer update message
            client_sock.sendall(struct.pack(">BxH", 0, 1))  # Type 0, padding, 1 rectangle
            # Send rectangle header
            client_sock.sendall(struct.pack(">HHHHI", x, y, w, h, 0))  # Raw encoding (0)
            # Send pixel data
            client_sock.sendall(pixel_data)
        except (ConnectionResetError, BrokenPipeError) as e:
            print(f"Client disconnected during full frame send: {e}")
            raise

    def send_diff(self, img, bbox, client_sock):
        x, y, x2, y2 = bbox
        w, h = x2 - x, y2 - y
        
        # Validate dimensions
        if w <= 0 or h <= 0:
            return
            
        # Limit update size to avoid large memory operations
        if w * h > 1000000:  # Limit to ~1M pixels
            # Send full frame when the update is large
            self.send_full_frame(img, client_sock)
            return
            
        # Crop the image to the changed area
        cropped = img.crop((x, y, x2, y2))
        pixel_data = cropped.tobytes()

        try:
            # Send framebuffer update message
            client_sock.sendall(struct.pack(">BxH", 0, 1))  # Type 0, padding, 1 rectangle
            # Send rectangle header
            client_sock.sendall(struct.pack(">HHHHI", x, y, w, h, 0))  # Raw encoding (0)
            # Send pixel data
            client_sock.sendall(pixel_data)
        except (ConnectionResetError, BrokenPipeError) as e:
            print(f"Client disconnected during diff send: {e}")
            raise