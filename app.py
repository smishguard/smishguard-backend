from flask import Flask, jsonify
from datetime import datetime
from model.MensajeSMS import MensajeSMS
from model.Alerta import Alerta
from model.Analisis import Analisis
import json

app = Flask(__name__)
application = app

@app.route('/')
def hello_world():
    return 'hello, world!'

@app.route("/ping")
def ping():
    return jsonify({"message": "pong"})

@app.route("/consultar-modelo")
def consultar_modelo():
    #mensajePrueba = MensajeSMS(1, "Prueba", datetime.now(), "+573107788388")
    analisisPrueba = Analisis(1, 1, 0.8, "otros detalles")
    #return jsonify({"Mensaje enviado": json.dumps(mensajePrueba.to_dict())})
    return jsonify({"Analisis realizado": json.dumps(analisisPrueba.to_dict())})

@app.route("/publicar-tweet")
def publicar_tweet():
    tweetPrueba = Alerta(1, "123 Tweet probando", datetime.now())
    return jsonify({"Publicacion": json.dumps(tweetPrueba.to_dict())})

if __name__ == '__main__':
    app.run(debug = True)
