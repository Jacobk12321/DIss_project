class InputHandler:
    def handle_key_event(self, keycode, pressed):
        print(f"⌨️ Key Event: {chr(keycode) if keycode < 128 else keycode} {'Pressed' if pressed else 'Released'}")

    def handle_mouse_event(self, x, y, button_mask):
        print(f"🖱️ Mouse Event at ({x}, {y}), Button Mask: {button_mask}")
