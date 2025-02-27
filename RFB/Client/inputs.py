import mouse
import keyboard

class InputHandler:
    def __init__(self, client):
        self.client = client  # Store the reference to RFBClient

    def listen_for_input(self):
        """Start listening for keyboard and mouse events."""
        mouse.hook(self.on_mouse_event)  # Correct mouse event handler
        keyboard.on_press(self.on_key_press)
        keyboard.on_release(self.on_key_release)

    def on_mouse_event(self, event):
        """Send mouse movement events to the server."""
        if hasattr(event, 'x') and hasattr(event, 'y'):
            self.client.send_pointer_event(event.x, event.y, 0)

    def on_key_press(self, event):
        """Send key press events to the server."""
        try:
            keycode = ord(event.name) if len(event.name) == 1 else 0
            self.client.send_key_event(keycode, 1)
        except TypeError:
            print(f"⚠️ Ignoring unsupported key: {event.name}")

    def on_key_release(self, event):
        """Send key release events to the server."""
        try:
            keycode = ord(event.name) if len(event.name) == 1 else 0
            self.client.send_key_event(keycode, 0)
        except TypeError:
            print(f"⚠️ Ignoring unsupported key: {event.name}")
