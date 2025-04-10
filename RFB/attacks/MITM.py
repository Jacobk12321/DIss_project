import socket
import threading

PROXY_HOST = '0.0.0.0'
PROXY_PORT = 5900

REAL_SERVER_HOST = '192.168.0.18'
REAL_SERVER_PORT = 5901  # Usually on 5900 (on 5901 for testing)

def relay(source, destination, label):
    try:
        while True:
            data = source.recv(4096)
            if not data:
                break

            # Basic payload inspection
            if label == "Client -> Server":
                print(f"[{label}] {len(data)} bytes")
                inspect_client_payload(data)
            elif label == "Server -> Client":
                print(f"[{label}] {len(data)} bytes")
                inspect_server_payload(data)

            destination.sendall(data)
    except Exception as e:
        print(f"[!] Relay error ({label}): {e}")
    finally:
        source.close()
        destination.close()

def inspect_client_payload(data):
    if data.startswith(b"RFB"):
        print("  ↳ Client sent handshake string:", data.decode(errors="ignore").strip())
    elif data.startswith(b"\x04"):  # Key event
        try:
            down_flag = data[1]
            keycode = int.from_bytes(data[2:6], 'big')
            print(f"  ↳ Key Event: {'DOWN' if down_flag else 'UP'} | Keycode: {keycode} ({chr(keycode) if keycode < 128 else 'non-ascii'})")
        except:
            pass
    elif data.startswith(b"\x05"):  # Mouse event
        try:
            button_mask = data[1]
            x = int.from_bytes(data[2:4], 'big')
            y = int.from_bytes(data[4:6], 'big')
            print(f"  ↳ Mouse Event: Button={button_mask}, X={x}, Y={y}")
        except:
            pass

def inspect_server_payload(data):
    if data.startswith(b"RFB"):
        print("  ↳ Server sent handshake response:", data.decode(errors="ignore").strip())
    elif data.startswith(b"\x00"):  # Framebuffer update
        print("  ↳ Framebuffer update from server.")

def handle_connection(client_sock):
    try:
        print("[+] Client connected")

        server_sock = socket.create_connection((REAL_SERVER_HOST, REAL_SERVER_PORT))
        print(f"[+] Connected to real server at {REAL_SERVER_HOST}:{REAL_SERVER_PORT}")

        threading.Thread(target=relay, args=(client_sock, server_sock, "Client -> Server")).start()
        threading.Thread(target=relay, args=(server_sock, client_sock, "Server -> Client")).start()

    except Exception as e:
        print(f"[!] Failed to connect to real server: {e}")
        client_sock.close()

def start_mitm():
    print(f"[*] MITM proxy listening on {PROXY_HOST}:{PROXY_PORT}")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((PROXY_HOST, PROXY_PORT))
        s.listen(5)
        while True:
            client_sock, addr = s.accept()
            print(f"[+] Accepted connection from {addr}")
            threading.Thread(target=handle_connection, args=(client_sock,), daemon=True).start()

if __name__ == "__main__":
    start_mitm()