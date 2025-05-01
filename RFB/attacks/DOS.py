import socket
import struct
import time
import random
from Crypto.Cipher import DES

def send_key_event(sock, down, keycode):
    """Send key event to VNC server"""
    msg = struct.pack(">BBI", 4, down, keycode)
    sock.sendall(msg)

def send_mouse_event(sock, button_mask, x, y):
    """Send mouse event to VNC server"""
    msg = struct.pack(">BBHH", 5, button_mask, x, y)
    sock.sendall(msg)

def reverse_bits(byte):
    """Reverse the bits in a byte"""
    return int('{:08b}'.format(byte)[::-1], 2)

def des_encrypt_challenge(challenge, password):
    """Encrypt the challenge using DES with the given password"""
    # Pad or trim the password to 8 bytes
    key = password.encode('latin-1').ljust(8, b'\x00')[:8]

    # Reverse the bits in each byte (VNC spec requirement)
    key = bytes([reverse_bits(b) for b in key])

    #  DES cipher
    des = DES.new(key, DES.MODE_ECB)
    
    # Split the challenge into two 8-byte blocks and encrypt each one
    return des.encrypt(challenge[:8]) + des.encrypt(challenge[8:])

def main():
    # Start timer
    start_time = time.time()
    
    sock = socket.create_connection(("192.168.0.18", 5900)) # change to IP of server

    # Handshake (RFB 3.8)
    sock.sendall(b"RFB 003.008\n")
    assert sock.recv(12).startswith(b"RFB 003")

    # Password authentication
    assert sock.recv(1) == b'\x02'
    challenge = sock.recv(16)
    PASSWORD = "secret"  # Your password here
    response = des_encrypt_challenge(challenge, PASSWORD)
    sock.sendall(response)
    assert sock.recv(4) == b'\x00\x00\x00\x00'  # Auth success
    print("Authenticated.")
    
    auth_time = time.time()
    print(f"Authentication completed in {auth_time - start_time:.3f} seconds")

    # Simulate fast keypress spam and mouse movements
    keycode = ord('A')
    for i in range(50000):
        iteration_start = time.time()
        
        send_key_event(sock, 1, keycode)  # Key down
        send_key_event(sock, 0, keycode)  # Key up
        
        # Simulate random mouse movements
        x = random.randint(0, 1023)
        y = random.randint(0, 767)
        send_mouse_event(sock, 0, x, y)  # Mouse move only
        
        # if random.random() < 0.2:  # 20% chance to click
        #     send_mouse_event(sock, 1, x, y)  # Mouse down
        #     send_mouse_event(sock, 0, x, y)  # Mouse up

        time.sleep(0.001)
        
        iteration_end = time.time()
        if i % 10 == 0:  # Print timing every 10 iterations
            print(f"Iteration {i+1}/60 took {(iteration_end - iteration_start) * 1000:.2f} ms")

    end_time = time.time()
    total_time = end_time - start_time
    stress_test_time = end_time - auth_time
    
    print("Finished stress test.")
    print(f"Total execution time: {total_time:.3f} seconds")
    print(f"Stress test portion: {stress_test_time:.3f} seconds")
    print(f"Average time per operation: {stress_test_time / 60 * 1000:.2f} ms")

if __name__ == "__main__":
    main()