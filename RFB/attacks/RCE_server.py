import socket
import os

def start_rce_server(host='0.0.0.0', port=5901):
    server_sock = socket.socket()
    server_sock.bind((host, port))
    server_sock.listen(1)
    print(f"[+] RCE Server listening on {host}:{port}")

    conn, addr = server_sock.accept()
    print(f"[+] Connection from {addr}")

    while True:
        data = conn.recv(1024).decode()
        if not data:
            break

        print(f"[!] Received: {data.strip()}")

        # Unsafe parsing (for demonstration only!)
        if data.startswith("RUN:"):
            cmd = data[4:]
            print(f"[*] Executing: {cmd}")
            os.system(cmd)

    conn.close()

if __name__ == "__main__":
    start_rce_server()
