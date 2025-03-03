import pygame

class Renderer:
    def __init__(self, width, height):
        """Initialize the rendering window with the given width and height."""
        pygame.init()
        self.width = width
        self.height = height
        self.window = pygame.display.set_mode((self.width, self.height))
        self.running = True

    def update_screen(self, x, y, width, height, pixel_data):
        """Update the portion of the screen with new pixel data."""
        try:
            # Convert raw pixel data to a pygame Surface
            image = pygame.image.fromstring(pixel_data, (width, height), "RGB")

            # Scale down the image if needed
            scaled_image = pygame.transform.scale(image, (self.width, self.height))

            # Draw image to screen
            self.window.blit(scaled_image, (0, 0))
            pygame.display.flip()  # Refresh the display

        except Exception as e:
            print(f"❌ Error updating screen: {e}")

    def run(self):
        """Run the rendering loop."""
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
        pygame.quit()
