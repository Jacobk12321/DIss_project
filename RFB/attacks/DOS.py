import socket
import struct
import time
import random
import threading
from Crypto.Cipher import DES
from PIL import Image, ImageTk
import tkinter as tk

# CONFIGURATION 
SERVER_HOST = "192.168.0.18"  # Change this to server ip
SERVER_PORT = 5900
PASSWORD = "secret"
AUTO_INPUT = True  #  automated input spam

# DES PASSWORD HANDLING 
def reverse_bits(byte):
    return int('{:08b}'.format(byte)[::-1], 2)

def des_key_from_password(password):
    key = password.ljust(8, '\x00')[:8]
    return bytes([reverse_bits(b) for b in key.encode("latin-1")])

# INPUT HANDLER 
class InputHandler:
    def __init__(self, sock):
        self.sock = sock

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

        print(f"[Client] Sending key event: keycode={keysym_code}, down={down_flag}")
        msg = struct.pack(">BBI", 4, down_flag, keysym_code)
        self.sock.sendall(msg)

    def send_mouse_event(self, event_type, x, y, num):
        button_mask = 1 if event_type == "4" else 0
        msg = struct.pack(">BBHH", 5, button_mask, x, y)
        self.sock.sendall(msg)

# RENDERER 
class Renderer:
    def __init__(self, on_key, on_mouse):
        self.window = tk.Tk()
        self.window.title("Tkinter VNC Client")
        self.canvas = tk.Canvas(self.window)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas_image = None

        self.img = None
        self.img_tk = None

        self.window.bind("<KeyPress>", on_key)
        self.window.bind("<KeyRelease>", on_key)
        self.canvas.bind("<ButtonPress>", on_mouse)
        self.canvas.bind("<ButtonRelease>", on_mouse)
        self.canvas.bind("<Motion>", on_mouse)

    def update_image(self, img):
        self.img = img
        self.img_tk = ImageTk.PhotoImage(img)
        if self.canvas_image is None:
            self.canvas_image = self.canvas.create_image(0, 0, anchor=tk.NW, image=self.img_tk)
        else:
            self.canvas.itemconfig(self.canvas_image, image=self.img_tk)
        self.window.update_idletasks()
        self.window.update()

    def start_loop(self):
        self.window.mainloop()


# MAIN LOGIC 
def recv_exact(sock, n):
    data = b""
    while len(data) < n:
        chunk = sock.recv(n - len(data))
        if not chunk:
            raise ConnectionError("Connection closed")
        data += chunk
    return data

def authenticate(sock):
    sock.sendall(b"RFB 003.008\n")
    if not recv_exact(sock, 12).startswith(b"RFB 003"):
        raise ConnectionError("Handshake failed")

    if recv_exact(sock, 1) != b'\x02':
        raise ConnectionError("Expected VNC auth")

    challenge = recv_exact(sock, 16)
    key = des_key_from_password(PASSWORD)
    des = DES.new(key, DES.MODE_ECB)
    response = des.encrypt(challenge[:8]) + des.encrypt(challenge[8:])
    sock.sendall(response)

    if recv_exact(sock, 4) != b'\x00\x00\x00\x00':
        raise ConnectionError("Authentication failed")
    

def receive_updates(sock, renderer):
    screen_image = None
    last_update_time = time.time()
    update_threshold = 1 / 30

    while True:
        try:
            msg_type = recv_exact(sock, 1)
            if not msg_type:
                break
            _ = recv_exact(sock, 1)
            num_rects = struct.unpack(">H", recv_exact(sock, 2))[0]

            updated = False
            for _ in range(num_rects):
                x, y, w, h, encoding = struct.unpack(">HHHHI", recv_exact(sock, 12))
                if encoding != 0:
                    print(f"[Client] Unsupported encoding: {encoding}")
                    continue

                pixel_data = recv_exact(sock, w * h * 3)
                patch = Image.frombuffer("RGB", (w, h), pixel_data)

                if screen_image is None:
                    screen_image = Image.new("RGB", (w, h))

                if x + w > screen_image.width or y + h > screen_image.height:
                    new_width = max(screen_image.width, x + w)
                    new_height = max(screen_image.height, y + h)
                    new_img = Image.new("RGB", (new_width, new_height))
                    new_img.paste(screen_image, (0, 0))
                    screen_image = new_img

                screen_image.paste(patch, (x, y))
                updated = True

            now = time.time()
            if updated and now - last_update_time >= update_threshold:
                renderer.update_image(screen_image)
                last_update_time = now

        except Exception as e:
            print(f"[Client] Update error: {e}")
            break

def stress_test_input(sock, auth_start):
    keycode = ord('A')
    n_tests = 1000
    start_time = time.time()

    for i in range(n_tests):
        iteration_start = time.time()

        send_key_event(sock, 1, keycode)  # Key down
        send_key_event(sock, 0, keycode)  # Key up

        x, y = random.randint(0, 1023), random.randint(0, 767)
        send_mouse_event(sock, 0, x, y)   # Mouse move

        # if random.random() < 0.2: # 20%
        #     send_mouse_event(sock ,1,x ,y) # mouse button down
        #     send_mouse_event(sock,0,x,y) # mouse button up 

        time.sleep(0.001)
        iteration_end = time.time()


        if i % 10 == 0:
            elapsed_ms = (iteration_end - iteration_start) * 1000
            print(f"Iteration {i+1} took {elapsed_ms:.2f} ms")

    
    end_time = time.time()

    total_exec_time = end_time - auth_start
    stress_test_time = end_time - start_time
    avg_op_time = (stress_test_time / n_tests) * 1000
    

    print("Finished stress test.")
    print(f"Total execution time: {total_exec_time:.3f} seconds")
    print(f"Stress test portion: {stress_test_time:.3f} seconds")
    print(f"Average time per operation: {avg_op_time:.2f} ms")

def send_key_event(sock, down, keycode):
    msg = struct.pack(">BBI", 4, down, keycode)
    sock.sendall(msg)

def send_mouse_event(sock, button_mask, x, y):
    msg = struct.pack(">BBHH", 5, button_mask, x, y)
    sock.sendall(msg)

def main():
    sock = socket.create_connection((SERVER_HOST, SERVER_PORT))
    
    auth_start = time.time()
    authenticate(sock)
    auth_end = time.time()
    
    print("[Client] Authenticated successfully")
    print(f"Authentication completed in {auth_end - auth_start:.3f} seconds")

    input_handler = InputHandler(sock)
    renderer = Renderer(
        on_key=lambda e: input_handler.send_key_event(str(e.type), e.keysym, getattr(e, "char", ""), getattr(e, "keycode", 0)),
        on_mouse=lambda e: input_handler.send_mouse_event(str(e.type), e.x, e.y, getattr(e, "num", 0))
    )

    threading.Thread(target=receive_updates, args=(sock, renderer), daemon=True).start()

    if AUTO_INPUT:
        threading.Thread(target=stress_test_input, args=(sock,auth_start), daemon=True).start()

    renderer.start_loop()

if __name__ == "__main__":
    main()
