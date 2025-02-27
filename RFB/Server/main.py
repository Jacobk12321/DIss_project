from rfb import RFBServer

if __name__ == "__main__":
    server = RFBServer(host="0.0.0.0", port=5900)
    server.run()