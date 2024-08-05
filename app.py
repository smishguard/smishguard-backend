from flask import Flask, jsonify, request
from info_test import info_test

app = Flask(__name__)
app.config.from_object('config.Config')

@app.route('/')
def hello_world():
    return 'hello, world!'

@app.route("/ping")
def ping():
    return jsonify({"message": "pong"})


if __name__ == '__main__':
    app.run(debug = True, port=4000)
