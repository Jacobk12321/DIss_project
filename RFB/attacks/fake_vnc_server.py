import socket
import struct
import os
import hashlib
from PIL import Image

FAKE_PASSWORD = "secret"
WIDTH, HEIGHT = 1024, 768
LOG_FILE = "passwords_log.txt"

def generate_fake_screen():
    """Create a fake screen"""
    img = Image.new("RGB", (WIDTH, HEIGHT), color=(30, 30, 160))
    return img.tobytes()

def recv_exact(sock, length):
    data = b""
    while len(data) < length:
        more = sock.recv(length - len(data))
        if not more:
            raise ConnectionError("Connection closed")
        data += more
    return data

def log_password(password_hash):
    with open(LOG_FILE, "a") as f:
        f.write(f"Received password hash: {password_hash.hex()}\n")

def start_fake_server(host='0.0.0.0', port=5900):
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind((host, port))
    server_sock.listen(1)
    print(f" Fake VNC server listening on {host}:{port}...")

    client_sock, addr = server_sock.accept()
    print(f"Connection from {addr}")

    # Step 1: Protocol Version Handshake
    client_version = recv_exact(client_sock, 12).decode().strip()
    print(f"[CLIENT] Version: {client_version}")
    client_sock.sendall(b"RFB 003.008\n")

    # Step 2: Authentication Type 
    client_sock.sendall(b'\x02')  # password (type 2)

    # Step 3: Challenge
    challenge = os.urandom(16)
    client_sock.sendall(challenge)

    response = recv_exact(client_sock, 16)
    expected = hashlib.md5(FAKE_PASSWORD.encode() + challenge).digest()

    log_password(response)

    if response == expected:
        print("Password match!")
        client_sock.sendall(b'\x00\x00\x00\x00')  # Success
    else:
        print("Password hash mismatch")
        client_sock.sendall(b'\x00\x00\x00\x01')  # Failure
        client_sock.close()
        return

    # Main loop
    try:
        while True:
            msg_type = recv_exact(client_sock, 1)
            if not msg_type:
                break

            if msg_type == b'\x03':  # FramebufferUpdateRequest
                _ = recv_exact(client_sock, 9)
                print(" Client requested framebuffer")

                fake_screen = generate_fake_screen()

                client_sock.sendall(b'\x00')  # FramebufferUpdate
                client_sock.sendall(b'\x00')  # Padding
                client_sock.sendall(struct.pack(">H", 1))  # 1 rectangle
                client_sock.sendall(struct.pack(">HHHHI", 0, 0, WIDTH, HEIGHT, 0))
                client_sock.sendall(fake_screen)

            elif msg_type == b'\x04':  # Key event
                down_flag, key = struct.unpack(">BI", recv_exact(client_sock, 5))
                print(f"[KEY] Keycode: {key}, down: {down_flag}")

            elif msg_type == b'\x05':  # Mouse event
                button_mask, x, y = struct.unpack(">BHH", recv_exact(client_sock, 5))
                print(f"[MOUSE] Buttons: {button_mask}, Position: ({x}, {y})")

            else:
                print(f"[?] Unknown msg type: {msg_type.hex()}")

    except Exception as e:
        print(f" Error: {e}")
    finally:
        print(" Client disconnected.")
        client_sock.close()

if __name__ == "__main__":
    start_fake_server()