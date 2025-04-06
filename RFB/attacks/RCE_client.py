import socket

s = socket.socket()
s.connect(("127.0.0.1", 5901))

# Safe: pop up message
payload = "RUN:msg Hello from RCE!"  # Use `notepad` or `msg` on Windows

s.sendall(payload.encode())
s.close()
