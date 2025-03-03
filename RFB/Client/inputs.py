import keyboard
import mouse

class InputHandler:
    def __init__(self, client):
        self.client = client

    def listen_for_input(self):
        """Listen for keyboard and mouse events."""
        keyboard.on_press(lambda e: self.client.send_key_event(ord(e.name[0]), 1) if len(e.name) == 1 else None)
        keyboard.on_release(lambda e: self.client.send_key_event(ord(e.name[0]), 0) if len(e.name) == 1 else None)

        def on_mouse_move(x, y):
            self.client.send_pointer_event(x, y, 0)

        mouse.hook(lambda e: on_mouse_move(e.x, e.y) if hasattr(e, 'x') else None)
