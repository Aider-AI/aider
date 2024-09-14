from flask import Flask
from routes import register_routes

app = Flask(__name__)

def create_app():
    register_routes(app)
    return app

if __name__ == "__main__":
    app.run(debug=True)
