import time
import struct
from PIL import ImageChops, Image
import mss

class FrameBuffer:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.previous_frame = None

    def significant_change(self, diff_img, pixel_threshold=2000):
        # Count changed pixels
        diff_data = diff_img.getdata()
        changed_pixels = sum(1 for pixel in diff_data if pixel != (0, 0, 0))
        return changed_pixels > pixel_threshold

    def stream_updates(self, client_sock):
        with mss.mss() as sct:
            monitor = sct.monitors[0]

            while True:
                time.sleep(1 / 30)  # ~30 FPS

                screenshot = sct.grab(monitor)
                img = Image.frombytes("RGB", (screenshot.width, screenshot.height), screenshot.rgb)

                if self.previous_frame is None:
                    self.previous_frame = img
                    self.send_full_frame(img, client_sock)
                    continue

                diff_image = ImageChops.difference(img, self.previous_frame)

                if not self.significant_change(diff_image):
                    continue  # Skip if too few pixels changed

                self.previous_frame = img
                bbox = diff_image.getbbox()
                if bbox:
                    self.send_diff(img, bbox, client_sock)

    def send_full_frame(self, img, client_sock):
        x, y = 0, 0
        w, h = img.size
        pixel_data = img.tobytes()

        try:
            client_sock.sendall(struct.pack(">BxH", 0, 1))
            client_sock.sendall(struct.pack(">HHHHI", x, y, w, h, 0))
            client_sock.sendall(pixel_data)
        except (ConnectionResetError, BrokenPipeError):
            print("Client disconnected.")

    def send_diff(self, img, bbox, client_sock):
        x, y = bbox[0], bbox[1]
        w, h = bbox[2] - x, bbox[3] - y
        cropped = img.crop((x, y, x + w, y + h))
        pixel_data = cropped.tobytes()

        try:
            client_sock.sendall(struct.pack(">BxH", 0, 1))
            client_sock.sendall(struct.pack(">HHHHI", x, y, w, h, 0))
            client_sock.sendall(pixel_data)
        except (ConnectionResetError, BrokenPipeError):
            print("Client disconnected.")