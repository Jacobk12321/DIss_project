import mouse
import keyboard

class InputHandler:
    def __init__(self, client):
        """Initialize the input handler and associate it with the client."""
        self.client = client  # Associate InputHandler with the client

    def listen_for_input(self):
        """Listen for mouse and keyboard inputs and send events to the client."""
        mouse.hook(lambda e: self.on_mouse_move(e) if hasattr(e, 'x') else None)
        keyboard.on_press(lambda e: self.on_key_event(e, True))
        keyboard.on_release(lambda e: self.on_key_event(e, False))

    def on_mouse_move(self, event):
        """Handle mouse movement and send pointer events."""
        try:
            self.client.send_pointer_event(event.x, event.y, 0)  #Uses `self.client`
        except AttributeError:
            print(" Error: Client object not initialized properly.")

    def on_key_event(self, event, is_pressed):
        """Handle key press events."""
        try:
            if len(event.name) == 1:  # Ensure it's a single character
                self.client.send_key_event(ord(event.name), int(is_pressed))
        except AttributeError:
            print("Error: Client object not initialized properly.")
