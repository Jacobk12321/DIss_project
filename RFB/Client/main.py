from rfb import RFBClient

if __name__ == "__main__":
    client = RFBClient("192.168.0.18", 5900) # IP of the server (Change this to your Server IP address)
    client.run()
