import socket

# Server's IP and port
HOST = '192.168.0.18' 
PORT = 5901 

# Create a socket and connect to the server
s = socket.socket()
s.connect((HOST, PORT))

# The command to trigger the notepad with the message
cmd = "notepad_message"  # This tells the server to open Notepad with the custom message

# Send the command to the server
s.sendall(f"RUN:{cmd}".encode())

# Receive the response from the server (the output of the command)
data = s.recv(2048).decode()
print(data)  # This will print what the server sent back (e.g., the status of the operation)

# Close the connection
s.close()
