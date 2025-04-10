import socket
import os
import hashlib

FAKE_PASSWORD = "secret"

def start_fake_server(host='0.0.0.0', port=5900):
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.bind((host, port))
    server_sock.listen(1)
    print(f"Listening for VNC connections on {host}:{port}...")

    client_sock, addr = server_sock.accept()
    print(f" Got connection from {addr}")

    # Receive version from client, send ours back
    version = client_sock.recv(12).decode()
    print(f"Client says: {version.strip()}")
    client_sock.sendall(b"RFB 003.008\n")

    # password auth
    client_sock.sendall(b'\x02')  # password auth
    challenge = os.urandom(16)
    client_sock.sendall(challenge)
    print("Sent challenge")

    # Receive the response
    response = client_sock.recv(16)
    print(f" Got password hash: {response.hex()}")

    # Compare with expected
    expected = hashlib.md5((FAKE_PASSWORD.encode() + challenge)).digest()
    print(f" Expected hash:   {expected.hex()}")
    if response == expected:
        print(f"Password match! (Client used {expected}!!)")
    else:
        print("Password mismatch.")

    client_sock.close()

if __name__ == "__main__":
    start_fake_server()
