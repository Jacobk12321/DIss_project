import struct
class InputHandler:
    def __init__(self, socket):
        self.sock = socket

    def send_key_event(self, event_type, keysym, char, keycode):
        down_flag = 1 if event_type == "2" else 0

        # Handle function keys F1–F12
        if keysym.startswith("F") and keysym[1:].isdigit():
            fn = int(keysym[1:])
            if 1 <= fn <= 12:
                keysym_code = 65469 + fn  # F1 = 65470
            else:
                return
        elif char:
            keysym_code = ord(char)
        else:
            keysym_code = keycode

        msg = struct.pack(">BBI", 4, down_flag, keysym_code)
        self.sock.sendall(msg)

    def send_mouse_event(self, event_type, x, y, num):
        button_mask = 1 if event_type == "4" else 0  # only left click support here
        msg = struct.pack(">BBHH", 5, button_mask, x, y)
        self.sock.sendall(msg)
