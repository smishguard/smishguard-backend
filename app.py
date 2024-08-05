from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/')
def hello_world():
    return 'hello, world!'

@app.route("/ping")
def ping():
    return jsonify({"message": "pong"})
