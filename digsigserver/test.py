from digsigserver import server

if __name__ == "__main__":
    server.app.run(host="127.0.0.1", port=9999)
