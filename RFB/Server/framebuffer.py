class FrameBuffer:
    """A simple framebuffer handler (placeholder)."""
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.pixels = [[(0, 0, 0) for _ in range(width)] for _ in range(height)]  # Black screen

    def get_frame(self):
        """Return raw pixel data (stub)."""
        return b'\x00' * (self.width * self.height * 3)  # Placeholder: Black screen
