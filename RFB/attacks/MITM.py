import socket
import threading

PROXY_HOST = '0.0.0.0'
PROXY_PORT = 5900

REAL_SERVER_HOST = '192.168.0.18'
REAL_SERVER_PORT = 5901  # Your actual RFB server

def forward(source, destination, label):
    try:
        while True:
            data = source.recv(4096)
            if not data:
                break
            print(f"[{label}] {len(data)} bytes")
            destination.sendall(data)
    except Exception as e:
        print(f"[{label}] Connection error: {e}")
    finally:
        source.close()
        destination.close()

def handle_client(client_sock):
    print("Client connected. Connecting to real server...")
    try:
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.connect((REAL_SERVER_HOST, REAL_SERVER_PORT))
    except Exception as e:
        print("[-] Could not connect to real server:", e)
        client_sock.close()
        return

    # Forward both directions
    threading.Thread(target=forward, args=(client_sock, server_sock, "C->S")).start()
    threading.Thread(target=forward, args=(server_sock, client_sock, "S->C")).start()

def start_proxy():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((PROXY_HOST, PROXY_PORT))
    server.listen(1)
    print(f"[*] MITM Proxy listening on {PROXY_HOST}:{PROXY_PORT}")
    while True:
        client_sock, _ = server.accept()
        threading.Thread(target=handle_client, args=(client_sock,), daemon=True).start()

if __name__ == "__main__":
    start_proxy()
