from sanic import Sanic
from sanic.worker.loader import AppLoader
from digsigserver import server

if __name__ == "__main__":
    loader = AppLoader(factory=server.create_app)
    app = loader.load()
    app.prepare(host="127.0.0.1", port=8888, debug=True)
    Sanic.serve(primary=app, app_loader=loader)
