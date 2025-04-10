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
        try:
            if len(event.name) == 1 or event.name.startswith('f'):  # support F-keys too
                key_code = ord(event.name) if len(event.name) == 1 else self.key_name_to_code(event.name)
                self.client.send_key_event(key_code, int(is_pressed))
        except AttributeError:
            print("Error: Client object not initialized properly.")

    def key_name_to_code(self, key_name):
        """Map key name (e.g., 'f12') to keycode (F12 = 123)"""
        function_keys = {
            'f1': 112, 'f2': 113, 'f3': 114, 'f4': 115, 'f5': 116, 'f6': 117,
            'f7': 118, 'f8': 119, 'f9': 120, 'f10': 121, 'f11': 122, 'f12': 123
        }
        return function_keys.get(key_name.lower(), 0)

