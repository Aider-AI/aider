from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route("/")
def home():
    return jsonify({"message": "Welcome to iXSpend backend!"})

@app.route("/api/hello")
def hello():
    return jsonify({"message": "Hello from iXSpend backend!"})

if __name__ == "__main__":
    app.run(debug=True)
