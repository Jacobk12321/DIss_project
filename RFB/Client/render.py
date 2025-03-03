import pygame
import threading

class Renderer:
    def __init__(self, client):
        pygame.init()
        self.client = client
        self.screen = pygame.display.set_mode((1920, 1080))
        self.running = True

    def update_screen(self, x, y, width, height, pixel_data):
        """Update the screen with received framebuffer data."""
        print(f"🖥️ Updating screen at ({x}, {y}) with size {width}x{height}")
        image = pygame.image.fromstring(pixel_data, (width, height), "RGB")
        self.screen.blit(image, (x, y))
        pygame.display.update()

    def run(self):
        """Keep the display open."""
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
