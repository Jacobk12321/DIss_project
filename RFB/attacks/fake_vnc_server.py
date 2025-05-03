import socket
import struct
import os
from Crypto.Cipher import DES
from PIL import Image
from datetime import datetime
import mss
import numpy as np


FAKE_PASSWORD = "secret"
WIDTH, HEIGHT = 1024, 768
LOG_FILE = "passwords_log.txt"


def generate_real_screen():
    with mss.mss() as sct:
        monitor = sct.monitors[1]  # full screen
        screenshot = sct.grab(monitor)
        img = Image.frombytes('RGB', screenshot.size, screenshot.rgb)
        img = img.resize((WIDTH, HEIGHT))
        return img.tobytes()


def recv_exact(sock, length):
    data = b""
    while len(data) < length:
        more = sock.recv(length - len(data))
        if not more:
            raise ConnectionError("Connection closed")
        data += more
    return data

def log_password(challenge, password_response, client_addr):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ip, port = client_addr
    with open(LOG_FILE, "a") as f:
        f.write("-+" * 75 + "\n")
        f.write(f"Timestamp: {timestamp}\n") # stores when the challenges were received
        f.write(f"Client: {ip}:{port}\n")
        f.write(f"Challenge: {challenge.hex()}\n")
        f.write(f"Response:  {password_response.hex()}\n")
        f.write("-+" * 75 + "\n")


def des_encrypt_challenge(challenge, password):
    key = password.encode('latin-1').ljust(8, b'\x00')[:8]

    def reverse_bits(byte):
        return int('{:08b}'.format(byte)[::-1], 2)

    key = bytes([reverse_bits(b) for b in key])
    des = DES.new(key, DES.MODE_ECB)

    return des.encrypt(challenge[:8]) + des.encrypt(challenge[8:])

def start_fake_server(host='0.0.0.0', port=5900):
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind((host, port))
    server_sock.listen(1)
    print(f"Fake VNC server listening on {host}:{port}...")

    client_sock, addr = server_sock.accept()
    print(f"Connection from {addr}")

    # Protocol Version Handshake
    client_version = recv_exact(client_sock, 12).decode().strip()
    print(f"[CLIENT] Version: {client_version}")
    client_sock.sendall(b"RFB 003.008\n")

    # Security type
    client_sock.sendall(b'\x02')  # type 2 (VNC auth)

    # Challenge
    challenge = os.urandom(16)
    client_sock.sendall(challenge)

    # Response
    response = recv_exact(client_sock, 16)
    expected = des_encrypt_challenge(challenge, FAKE_PASSWORD)
    log_password(challenge, response , addr)

    if response == expected:
        print(" Password correct")
        client_sock.sendall(b'\x00\x00\x00\x00')  # Auth success
    else:
        print(" Password incorrect")
        client_sock.sendall(b'\x00\x00\x00\x01')  # Auth failed
        client_sock.close()
        return

    try:
        while True:
            msg_type = recv_exact(client_sock, 1)
            if not msg_type:
                break

            real_screen = generate_real_screen()
            
            client_sock.sendall(b'\x00')  # FramebufferUpdate
            client_sock.sendall(b'\x00')  # Padding
            client_sock.sendall(struct.pack(">H", 1))  # 1 rectangle
            client_sock.sendall(struct.pack(">HHHHI", 0, 0, WIDTH, HEIGHT, 0))
            client_sock.sendall(real_screen)

            if msg_type == b'\x04':  # Key event
                down_flag, key = struct.unpack(">BI", recv_exact(client_sock, 5))
                print(f"[KEY] Keycode: {key}, down: {down_flag}")

            if msg_type == b'\x05':  # Mouse event
                button_mask, x, y = struct.unpack(">BHH", recv_exact(client_sock, 5))
                print(f"[MOUSE] Buttons: {button_mask}, Position: ({x}, {y})")

            else:
                print(f"[?] Unknown msg type: {msg_type.hex()}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        print("Client disconnected.")
        client_sock.close()

if __name__ == "__main__":
    start_fake_server()