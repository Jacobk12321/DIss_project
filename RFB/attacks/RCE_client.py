import socket

# Server's IP and port
HOST = '192.168.0.18' # needs to change to the server IP
PORT = 5901 

# Create a socket and connect to the server
s = socket.socket()
s.connect((HOST, PORT))

# The command to trigger the notepad with the message
cmd = "notepad_message"  # open Notepad with the custom message

# Send the command to the server
s.sendall(f"RUN:{cmd}".encode())

# Receive the response from the server (the output of the command)
data = s.recv(2048).decode()
print(data)  

# Close the connection
s.close()
