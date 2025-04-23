import time
import struct

class InputHandler:
    def __init__(self, socket):
        self.sock = socket

    def send_key_event(self, event_type, keysym, char, keycode):
        down_flag = 1 if event_type == "2" else 0

        if keysym.startswith("F") and keysym[1:].isdigit():
            fn = int(keysym[1:])
            if 1 <= fn <= 12:
                keysym_code = 65469 + fn
            else:
                return
        elif char:
            keysym_code = ord(char)
        else:
            keysym_code = keycode

        print(f"[Client] Sending key event: keycode={keysym_code}, down={down_flag}, time={time.time():.6f}")
        msg = struct.pack(">BBI", 4, down_flag, keysym_code)
        self.sock.sendall(msg)

    def send_mouse_event(self, event_type, x, y, num):
        button_mask = 1 if event_type == "4" else 0  # Only left click for now

        if event_type == "4":
            print(f"[Client] Sending MOUSE DOWN at ({x},{y}) - Button: Left, time={time.time():.6f}")
        elif event_type == "5":
            print(f"[Client] Sending MOUSE UP at ({x},{y}) - Button: Left, time={time.time():.6f}")
        elif event_type == "6":
            print(f"[Client] Sending MOUSE MOVE at ({x},{y}), time={time.time():.6f}")

        msg = struct.pack(">BBHH", 5, button_mask, x, y)
        self.sock.sendall(msg)
