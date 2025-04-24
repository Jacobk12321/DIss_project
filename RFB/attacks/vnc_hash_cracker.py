import hashlib

# captured challenge and hash from the client
captured_challenge = bytes.fromhex("3defc5e677e85540a98bcfeefdb7566e")
captured_response = bytes.fromhex("04ae41e76a5c9405a832a633371eaf3a")

# Your wordlist
wordlist = [
    "123456",
    "password",
    "admin",
    "letmein",
    "qwerty",
    "secret",  # correct for fake server
    "welcome",
]

def crack_vnc_password(challenge, expected_hash, wordlist):
    print(f" Starting brute-force...")
    for password in wordlist:
        candidate = hashlib.md5(password.encode() + challenge).digest()
        if candidate == expected_hash:
            print(f" Password cracked: '{password}'")
            return password
    print("Password not found in wordlist.")
    return None

if __name__ == "__main__":
    crack_vnc_password(captured_challenge, captured_response, wordlist)